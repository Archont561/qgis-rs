//! The checks that are not any one package's: the C++ format gate, the TOML
//! canonicality gate, the published-package contents check, and the one
//! environment repair a conda QGIS prefix needs.

use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};

use crate::util::{cpp_sources, repo_root, run};

/// clang-format gate for the C++ shim.
///
/// With arguments it checks exactly those files — that is how lefthook passes
/// the staged ones — and with none it checks the whole shim. Assumes it runs
/// inside the `default` pixi environment, which is where clang-tools lives.
pub fn check_cpp(files: &[String]) -> Result<()> {
    let paths: Vec<PathBuf> = if files.is_empty() {
        cpp_sources()
    } else {
        files.iter().map(PathBuf::from).collect()
    };
    if paths.is_empty() {
        println!("check-cpp: no C++ sources to check");
        return Ok(());
    }
    let mut args = vec!["--dry-run".to_string(), "--Werror".to_string()];
    args.extend(paths.iter().map(|path| path.display().to_string()));
    run("clang-format", args)
}

/// The manifests kept in taplo's canonical form.
///
/// Only these two are: the rest of the repository uses the aligned-`=` style
/// on purpose, and running taplo over them would rewrite a deliberate choice.
/// Public for `tests/lints.rs`, which asserts both files still exist.
pub const CANONICAL_TOML: &[&str] = &["pixi.toml", "pixi-sandbox.toml"];

/// taplo canonicality check. Arguments (staged files) override the list above.
pub fn lint_toml(files: &[String]) -> Result<()> {
    let targets: Vec<String> = if files.is_empty() {
        CANONICAL_TOML.iter().map(ToString::to_string).collect()
    } else {
        files.to_vec()
    };
    let mut args = vec!["fmt".to_string(), "--check".to_string()];
    args.extend(targets);
    run("taplo", args)
}

/// Assert a package directory contains everything its `files` list promises,
/// before `npm publish` finds out for us in a way that cannot be unpublished.
///
/// An entry ending in `/` is checked as a directory; an entry containing `*`
/// is checked as a glob that must match at least once.
pub fn pack_check(package_dir: &str, required: &[String]) -> Result<()> {
    let directory = repo_root().join(package_dir);
    if !directory.is_dir() {
        bail!("no such package directory: {}", directory.display());
    }

    let mut missing = Vec::new();
    for entry in required {
        let present = if let Some(name) = entry.strip_suffix('/') {
            directory.join(name).is_dir()
        } else if entry.contains('*') {
            glob_matches(&directory, entry)?
        } else {
            directory.join(entry).exists()
        };
        if !present {
            missing.push(entry.clone());
        }
    }

    if !missing.is_empty() {
        for entry in &missing {
            eprintln!("missing from package: {entry} (did the build run?)");
        }
        bail!("{} entries missing from {package_dir}", missing.len());
    }
    println!("package contents verified in {package_dir}");
    Ok(())
}

/// Whether at least one file matches a `*`-pattern inside `directory`.
///
/// Only the forms the packages actually use are supported — one `*` in the
/// file-name part, optionally under a subdirectory (`qgis-rs.*.node`,
/// `dist/*.whl`) — which is why this is twenty lines instead of a glob
/// dependency nobody else in the workspace needs.
pub fn glob_matches(directory: &Path, pattern: &str) -> Result<bool> {
    let (sub_directory, file_pattern) = match pattern.rsplit_once('/') {
        Some((parent, name)) => (directory.join(parent), name),
        None => (directory.to_path_buf(), pattern),
    };
    let (prefix, suffix) = file_pattern
        .split_once('*')
        .context("a glob needs exactly one '*' in its file name")?;
    let Ok(entries) = std::fs::read_dir(&sub_directory) else {
        // A missing directory is a missing match, not an error: that is
        // exactly what this check reports on.
        return Ok(false);
    };
    for entry in entries {
        let name = entry?.file_name().to_string_lossy().into_owned();
        if name.len() >= prefix.len() + suffix.len()
            && name.starts_with(prefix)
            && name.ends_with(suffix)
        {
            return Ok(true);
        }
    }
    Ok(false)
}

/// The trees that hold hand-written source, as opposed to build output.
///
/// Public for `tests/lints.rs`: which directories count as source is the whole
/// content of [`check_sources`].
pub const SOURCE_TREES: &[&str] = &["crates", "py-packages", "ts-packages", "scripts"];

/// Directory segments inside those trees that are *not* source.
const BUILD_OUTPUT: &[&str] = &[
    "node_modules/",
    "__pycache__/",
    "/dist/",
    "/build/",
    "/target/",
    "/.pixi/",
    "/.venv/",
];

/// File extensions a reader would call source.
const SOURCE_EXTENSIONS: &[&str] = &[
    ".py", ".pyi", ".rs", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".cpp", ".h", ".hpp",
];

/// Whether `path` is a source file that belongs in the repository.
///
/// Dot-prefixed names are excluded: a generated `.napi-generated.d.ts` sits
/// next to the addon it describes and is ignored on purpose. Public because
/// this predicate, not the git plumbing around it, is what the test pins.
#[must_use]
pub fn looks_like_source(path: &str) -> bool {
    let name = path.rsplit('/').next().unwrap_or(path);
    if name.starts_with('.') {
        return false;
    }
    if BUILD_OUTPUT.iter().any(|segment| path.contains(segment)) {
        return false;
    }
    SOURCE_EXTENSIONS
        .iter()
        .any(|extension| name.ends_with(extension))
}

/// Fail if a source file inside a package tree is ignored by git.
///
/// This exists because it already happened: `.gitignore` ignores `_*` so that
/// build droppings stay out, re-included a list of Python module names by
/// hand, and the day `_api.py` and `_transport.py` were written nobody
/// remembered to extend the list. Both files were real source, both were
/// invisible to `git status`, and the whole Python client was pushed as a
/// package that could not import itself — a local gate that ran against the
/// files on disk said nothing, because on disk they were there.
///
/// An ignored file that is *not* source — a wheel, an addon, a generated
/// `.d.ts` — is exactly what the ignore rules are for and is not reported.
pub fn check_sources() -> Result<()> {
    let root = repo_root();
    if !root.join(".git").exists() {
        println!("check-sources: not a git checkout, nothing to compare");
        return Ok(());
    }

    let mut args = vec![
        "ls-files".to_string(),
        "--others".to_string(),
        "--ignored".to_string(),
        "--exclude-standard".to_string(),
        "--".to_string(),
    ];
    args.extend(SOURCE_TREES.iter().map(ToString::to_string));
    let listed = crate::util::capture("git", args)?;
    if !listed.status.success() {
        bail!(
            "git ls-files failed: {}",
            String::from_utf8_lossy(&listed.stderr)
        );
    }

    let hidden: Vec<&str> = std::str::from_utf8(&listed.stdout)
        .context("git listed a path that is not UTF-8")?
        .lines()
        .filter(|path| looks_like_source(path))
        .collect();

    if !hidden.is_empty() {
        for path in &hidden {
            eprintln!("ignored but looks like source: {path}");
        }
        bail!(
            "{} source file(s) are hidden by .gitignore — commit them, or narrow the ignore rule",
            hidden.len()
        );
    }
    println!(
        "check-sources: every source file in {} trees is visible to git",
        SOURCE_TREES.len()
    );
    Ok(())
}

/// Link libqca under the Qt5 soname QGIS still dlopens, whichever flavour
/// conda-forge installed. Idempotent, so every task that needs a live QGIS can
/// call it unconditionally.
pub fn setup_qca() -> Result<()> {
    let prefix = std::env::var("CONDA_PREFIX")
        .context("CONDA_PREFIX is not set — run this under `pixi run -e default`")?;
    let lib = Path::new(&prefix).join("lib");
    let target = lib.join("libqca-qt5.so.2");

    let source = if lib.join("libqca-qt6.so.2").exists() {
        lib.join("libqca-qt6.so.2")
    } else if lib.join("libqca-qt5.so.2.3.12").exists() {
        lib.join("libqca-qt5.so.2.3.12")
    } else {
        bail!("no libqca found under {}", lib.display());
    };

    // Replace rather than fail: the link may point at a library from a prefix
    // that has since been rebuilt.
    if target.exists() || target.is_symlink() {
        std::fs::remove_file(&target)
            .with_context(|| format!("cannot replace {}", target.display()))?;
    }
    std::os::unix::fs::symlink(&source, &target)
        .with_context(|| format!("cannot link {} -> {}", target.display(), source.display()))?;
    println!("{} -> {}", target.display(), source.display());
    Ok(())
}
