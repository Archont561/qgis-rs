//! The release pipeline: verify, build, checksum, publish.
//!
//! Each step is a subcommand rather than a workflow step, so `release.yml` is
//! a list of one-line `pixi run xtask release …` calls and the same sequence
//! can be rehearsed locally before a tag exists.

use std::fs;
use std::path::Path;
use std::thread::sleep;
use std::time::Duration;

use anyhow::{bail, Context, Result};
use clap::Subcommand;

use crate::ci::{cargo, plain, turbo_run};
use crate::util::{capture, pixi, repo_root, run_in, step};

/// The crates published to crates.io, in dependency order.
///
/// qgis-py / qgis-sdk / qgis-node are deliberately absent: they are PyO3 and
/// NAPI cores whose only consumers are the wheels and the npm package built
/// from this same tag, and a crates.io copy of an extension module is a
/// download nobody can link against. qgis-protocol and qgis-engine ARE here —
/// they are ordinary libraries, and the transport is the thing a third-party
/// binding would want to depend on.
/// Public so `tests/release.rs` can assert the order and the exclusions: this
/// list is a dependency graph flattened by hand, and the test is what keeps it
/// honest.
pub const CRATES: &[&str] = &[
    "qgis-sys",
    "qgis-styles",
    "qgis-render",
    "qgis-protocol",
    "qgis-engine",
    "qgis-server",
    "qgis-mcp",
    "qgis-cli",
];

/// The Python distributions maturin builds wheels for.
const PY_DISTRIBUTIONS: &[&str] = &["py-packages/qgis-py", "py-packages/qgis-sdk"];

/// The npm packages that are packed and uploaded.
const NPM_PACKAGES: &[&str] = &["ts-packages/qgis-node", "ts-packages/qgis-sdk"];

#[derive(Debug, Subcommand)]
pub enum Release {
    /// Check a tag against the workspace version and every manifest.
    VerifyVersion {
        /// The tag being released, e.g. `v1.2.3`.
        tag: String,
    },
    /// Derive the next version, rewrite the manifests, regenerate the changelog.
    Prepare {
        /// Release this exact version instead of the one convco derives.
        version: Option<String>,
    },
    /// Build every immutable release asset into dist/.
    BuildArtifacts,
    /// One SHA256SUMS over every release asset.
    Checksums,
    /// Publish the Rust crates to crates.io, in dependency order.
    PublishCrates,
    /// Publish the npm tarballs to GitHub Packages.
    PublishGithubPackages,
}

pub fn run(step: Release) -> Result<()> {
    match step {
        Release::VerifyVersion { tag } => verify_version(&tag),
        Release::Prepare { version } => prepare(version.as_deref()),
        Release::BuildArtifacts => build_artifacts(),
        Release::Checksums => checksums(),
        Release::PublishCrates => publish_crates(),
        Release::PublishGithubPackages => publish_github_packages(),
    }
}

/// The workspace version, as `scripts/version.ts` reports it.
///
/// That script stays TypeScript: it is the one tool that rewrites every
/// manifest in the repository, it has the JSON/TOML surgery to do it, and
/// `pixi run version` is how CI already asks. xtask calls it rather than
/// reimplementing it — two sources of truth for "the version" is exactly the
/// failure this pipeline exists to prevent.
fn workspace_version() -> Result<String> {
    let output = capture("pixi", ["run", "-e", "bun", "version"])?;
    if !output.status.success() {
        bail!(
            "`pixi run version` failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
    let text = String::from_utf8_lossy(&output.stdout);
    let version = text
        .lines()
        .rfind(|line| !line.trim().is_empty())
        .context("`pixi run version` printed nothing")?
        .trim()
        .to_string();
    Ok(version)
}

/// The tag, the workspace manifest and every package manifest must describe
/// one release. Run before anything is built, let alone uploaded.
fn verify_version(tag: &str) -> Result<()> {
    let version = workspace_version()?;
    if tag != format!("v{version}") {
        bail!("tag {tag} does not match workspace version {version}");
    }
    pixi("bun", ["version-check"])?;
    println!("release {tag} verified against pixi.toml [workspace] version {version}");
    Ok(())
}

/// Derive the next version from the conventional-commit history, write it into
/// every manifest, regenerate the changelog, and refresh the lockfiles that
/// embed a version.
fn prepare(requested: Option<&str>) -> Result<()> {
    let next = match requested {
        Some(version) => version.to_string(),
        None => {
            let output = capture(
                "pixi",
                ["run", "-e", "default", "convco", "version", "--bump"],
            )?;
            String::from_utf8_lossy(&output.stdout)
                .lines()
                .rfind(|line| !line.trim().is_empty())
                .context("convco produced no version")?
                .trim()
                .to_string()
        }
    };
    if next.is_empty() {
        bail!("convco produced no version");
    }

    let existing = capture(
        "git",
        [
            "rev-parse",
            "--verify",
            "--quiet",
            &format!("refs/tags/v{next}"),
        ],
    )?;
    if existing.status.success() {
        bail!("v{next} already exists; there are no releasable commits");
    }

    step(&format!("preparing v{next}"));
    pixi("bun", ["version-set", &next])?;
    pixi(
        "default",
        [
            "convco",
            "changelog",
            "--unreleased",
            &next,
            "--output",
            "CHANGELOG.md",
        ],
    )?;

    // The lockfiles embed the workspace member versions that just changed.
    pixi("bun", ["bun", "install", "--lockfile-only"])?;
    cargo(&["metadata", "--format-version", "1"])?;
    plain("pixi", &["lock"])?;

    // Nothing is committed until every manifest agrees on the new number.
    pixi("bun", ["version-check"])?;
    println!("{next}");
    Ok(())
}

/// Build every immutable release asset into dist/, before a single network
/// publication is attempted. A failed build is release-blocking; only the
/// registry uploads that follow are allowed to fail independently.
fn build_artifacts() -> Result<()> {
    let root = repo_root();
    let dist = root.join("dist");
    if dist.exists() {
        fs::remove_dir_all(&dist).context("cannot clear dist/")?;
    }
    for sub in ["pypi", "npm", "conda"] {
        fs::create_dir_all(dist.join(sub))?;
    }

    step("Python wheels");
    // qgis-py ships the prebuilt qgis-cli binary inside its wheel. Stage it
    // from this runner before maturin packs the wheel, so every platform's
    // wheel carries the binary built on that platform.
    pixi(
        "default",
        ["python", "py-packages/qgis-py/scripts/stage_cli.py"],
    )?;
    for distribution in PY_DISTRIBUTIONS {
        pixi(
            "default",
            [
                "maturin",
                "build",
                "--release",
                "--manifest-path",
                &format!("{distribution}/pyproject.toml"),
                "--out",
                &dist.join("pypi").display().to_string(),
            ],
        )
        .or_else(|_| {
            // maturin reads a pyproject through `-m`; older versions only
            // accept being run from the distribution directory, which is what
            // the shell script did. Fall back to that rather than pin a
            // maturin minor in two places.
            run_in(
                &root.join(distribution),
                "maturin",
                [
                    "build",
                    "--release",
                    "--out",
                    &dist.join("pypi").display().to_string(),
                ],
            )
        })?;
    }

    step("npm tarballs");
    // The addon has to be compiled before it can be packed: `files` lists
    // qgis-node.*.node, and pack:check is what proves it is there.
    turbo_run(&[
        "build",
        "--filter=@archont561/qgis-node",
        "--filter=@archont561/qgis-sdk",
    ])?;
    turbo_run(&["pack:check"])?;
    for package in NPM_PACKAGES {
        run_in(
            &root.join(package),
            "bun",
            [
                "pm",
                "pack",
                "--destination",
                &dist.join("npm").display().to_string(),
            ],
        )?;
    }

    step("conda packages");
    plain(
        "pixi",
        &["publish", "--target-dir", "dist/conda", "--clean"],
    )?;

    step("artifacts");
    for path in walk(&dist) {
        println!("{}", path.display());
    }
    Ok(())
}

/// Every file under `directory`, sorted — the stable order the checksum file
/// and the artifact listing both need.
fn walk(directory: &Path) -> Vec<std::path::PathBuf> {
    let mut files: Vec<_> = walkdir::WalkDir::new(directory)
        .into_iter()
        .filter_map(std::result::Result::ok)
        .filter(|entry| entry.file_type().is_file())
        .map(walkdir::DirEntry::into_path)
        .collect();
    files.sort();
    files
}

/// One SHA256SUMS over every release asset, in a stable order so the file is
/// reproducible across runners.
fn checksums() -> Result<()> {
    let dist = repo_root().join("dist");
    let sums_path = dist.join("SHA256SUMS");
    let files: Vec<_> = walk(&dist)
        .into_iter()
        .filter(|path| path != &sums_path)
        .collect();
    if files.is_empty() {
        bail!("no artifacts under dist/ — run `xtask release build-artifacts` first");
    }

    let mut sums = String::new();
    for path in files {
        let relative = path.strip_prefix(repo_root()).unwrap_or(&path);
        // sha256sum rather than a hashing crate: the file has to match what a
        // consumer verifies with the same tool, byte for byte including the
        // two-space separator, and it is already in the environment.
        let output = capture("sha256sum", [relative.display().to_string()])?;
        if !output.status.success() {
            bail!("sha256sum failed for {}", relative.display());
        }
        sums.push_str(&String::from_utf8_lossy(&output.stdout));
    }
    fs::write(&sums_path, &sums).context("cannot write dist/SHA256SUMS")?;
    print!("{sums}");
    Ok(())
}

/// Publish the Rust crates to crates.io in dependency order.
///
/// Two things make this more than a loop:
///
/// 1. crates.io index propagation. A dependent crate can be rejected seconds
///    after its dependency was accepted, so each upload is retried with a
///    backoff.
/// 2. Immutable duplicates. An earlier, partially successful release attempt
///    leaves some crates already published; that must not block the rest.
fn publish_crates() -> Result<()> {
    if std::env::var("CARGO_REGISTRY_TOKEN").is_err() {
        bail!("CARGO_REGISTRY_TOKEN is not set");
    }
    for crate_name in CRATES {
        publish_one(crate_name)?;
    }
    Ok(())
}

fn publish_one(crate_name: &str) -> Result<()> {
    for attempt in 1..=6_u32 {
        let output = capture(
            "pixi",
            [
                "run",
                "-e",
                "default",
                "cargo",
                "publish",
                "--locked",
                "--package",
                crate_name,
            ],
        )?;
        let combined = format!(
            "{}{}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );
        print!("{combined}");
        if output.status.success() {
            println!("published {crate_name}");
            return Ok(());
        }
        if already_published(&combined) {
            println!(
                "::warning title={crate_name} was not uploaded::already on crates.io from an earlier attempt; continuing"
            );
            return Ok(());
        }
        println!("attempt {attempt} for {crate_name} failed; waiting for index propagation");
        sleep(Duration::from_secs(u64::from(attempt) * 15));
    }
    bail!("giving up on {crate_name}")
}

/// Whether a `cargo publish` rejection means "this version is already there".
pub fn already_published(output: &str) -> bool {
    let lowered = output.to_lowercase();
    lowered.contains("already exists")
        || (lowered.contains("already") && lowered.contains("uploaded"))
}

/// Publish the npm tarballs to GitHub Packages.
///
/// GitHub Packages is a separate npm registry and does not implement npmjs
/// Trusted Publishing, so it needs the workflow token. The token is written to
/// a throwaway npmrc rather than the user config: it must never end up applied
/// to the npmjs upload, which mints its own short-lived OIDC credential and
/// would silently prefer a static token if one were present.
fn publish_github_packages() -> Result<()> {
    if std::env::var("NODE_AUTH_TOKEN").is_err() {
        bail!("NODE_AUTH_TOKEN is not set");
    }
    let temp = std::env::var("RUNNER_TEMP").unwrap_or_else(|_| "/tmp".to_string());
    let config = Path::new(&temp).join("github-packages.npmrc");
    fs::write(
        &config,
        "@archont561:registry=https://npm.pkg.github.com\n\
         //npm.pkg.github.com/:_authToken=${NODE_AUTH_TOKEN}\n",
    )
    .with_context(|| format!("cannot write {}", config.display()))?;

    let tarballs = walk(&repo_root().join("dist/npm"));
    let tarballs: Vec<_> = tarballs
        .into_iter()
        .filter(|path| path.extension().is_some_and(|extension| extension == "tgz"))
        .collect();
    if tarballs.is_empty() {
        bail!("no tarballs under dist/npm — run `xtask release build-artifacts` first");
    }

    for tarball in tarballs {
        let status = std::process::Command::new("npm")
            .args([
                "publish",
                "--registry",
                "https://npm.pkg.github.com",
                &tarball.display().to_string(),
            ])
            .env("NPM_CONFIG_USERCONFIG", &config)
            .current_dir(repo_root())
            .status()
            .context("cannot start npm")?;
        if !status.success() {
            bail!("npm publish failed for {}", tarball.display());
        }
    }
    Ok(())
}
