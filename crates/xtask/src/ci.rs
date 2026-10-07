//! The gate, and what to print when it fails.
//!
//! `pixi run xtask ci` locally and the CI workflow run exactly this function,
//! so "passes on my machine" and "passes in Actions" cannot mean different
//! things.

use std::fs;
use std::io::Write;
use std::path::Path;

use anyhow::{bail, Context, Result};

use crate::util::{capture, pixi, pixi_with_env, repo_root, run, step};

/// The docs site is excluded from every fan-out below: it is built and
/// deployed by docs.yml, and pulling Astro into the gate would double the
/// critical path for a surface that cannot break the libraries.
const NOT_DOCS: &str = "--filter=!qgis-rs-docs";

/// An in-process check at the front of the gate.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RepoLint {
    CheckSources,
    CheckBoundaries,
    CheckApiManifest,
    ValidateBridgeFixtures,
    CheckProtocolDocs,
    CheckApiOperations,
}

impl RepoLint {
    /// Stable command spelling, exposed so the gate order is testable.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::CheckSources => "check-sources",
            Self::CheckBoundaries => "check-boundaries",
            Self::CheckApiManifest => "api-manifest --check",
            Self::ValidateBridgeFixtures => "validate-bridge-fixtures",
            Self::CheckProtocolDocs => "check-protocol-docs",
            Self::CheckApiOperations => "check-api-operations",
        }
    }

    fn run(self) -> Result<()> {
        match self {
            Self::CheckSources => crate::lints::check_sources(),
            Self::CheckBoundaries => crate::boundaries::check(&repo_root()),
            Self::CheckApiManifest => crate::api_manifest::verify_repository(&repo_root()),
            Self::ValidateBridgeFixtures => {
                crate::bridge_fixtures::run(&repo_root().join("test-fixtures/bridge"))
            }
            Self::CheckProtocolDocs => crate::protocol_docs::run(&repo_root()),
            Self::CheckApiOperations => crate::api_manifest::run_wire_operations_check(),
        }
    }
}

/// In-process checks at the front of the gate, in execution order.
///
/// Public for `tests/ci.rs`: this executable list prevents generated
/// native-manager fragments from drifting before a compiler sees them.
pub const REPO_LINTS: &[RepoLint] = &[
    RepoLint::CheckSources,
    RepoLint::CheckBoundaries,
    RepoLint::CheckApiManifest,
    RepoLint::ValidateBridgeFixtures,
    RepoLint::CheckProtocolDocs,
    RepoLint::CheckApiOperations,
];

/// A slice of the gate that can run on its own runner.
///
/// The split exists so CI can fail a formatting violation in under a minute
/// instead of after the test fan-out, and it lives **here** rather than in
/// YAML on purpose: a workflow that re-spelled these steps would be a second
/// gate, free to drift from the one a contributor runs ([D10]). `ci.yml`
/// calls `xtask ci --stage <name>`, `pixi run ci` calls every stage in this
/// order, and [`tests/ci.rs`] asserts the two agree.
///
/// [D10]: /.knowledge/decisions/D10-xtask-over-shell-scripts.md
#[derive(Debug, Clone, Copy, PartialEq, Eq, clap::ValueEnum)]
pub enum Stage {
    /// Repo-wide lints and the format-drift gate. Seconds, and no compile.
    Repo,
    /// The package lint fan-out — clippy and biome.
    Lint,
    /// The test fan-out plus the publishable-package check.
    Test,
    /// The coverage producers: the most expensive, and nothing gates on them.
    Coverage,
}

impl Stage {
    /// Stable command spelling, as `--stage` accepts it.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Repo => "repo",
            Self::Lint => "lint",
            Self::Test => "test",
            Self::Coverage => "coverage",
        }
    }

    /// The gate steps this stage owns, in execution order.
    ///
    /// Public because the partition is the contract: `tests/ci.rs` checks that
    /// concatenating these in [`STAGES`] order reproduces [`GATE_STEPS`]
    /// exactly, so a step cannot be dropped from CI by being moved between
    /// stages, nor run twice by being listed in both.
    #[must_use]
    pub const fn steps(self) -> &'static [&'static str] {
        match self {
            Self::Repo => &["repo lints", "format drift gate"],
            Self::Lint => &["package lints"],
            Self::Test => &["tests", "publishable-package contents"],
            Self::Coverage => &["coverage"],
        }
    }

    /// Run just this stage.
    fn run(self, offline: bool) -> Result<()> {
        match self {
            Self::Repo => {
                step("repo lints (sources, boundaries, API manifest, taplo, actionlint)");
                // Keep these in-process and ordered as REPO_LINTS records: each
                // costs milliseconds and catches an invalid repository before
                // any compile.
                for lint in REPO_LINTS {
                    lint.run()?;
                }
                pixi("default", ["xtask", "lint-toml"])?;
                pixi("default", ["actionlint"])?;

                step("format drift gate");
                turbo(&["format", NOT_DOCS], offline)?;
                assert_no_drift()
            }
            Self::Lint => {
                step("package lints (turbo fan-out)");
                turbo(&["lint", NOT_DOCS], offline)
            }
            Self::Test => {
                step("tests (turbo fan-out; each package builds what it needs)");
                turbo(&["test", NOT_DOCS], offline)?;

                // Filtered like every other fan-out: the docs site publishes
                // nothing, and without the filter turbo pulls its Astro build
                // into the gate as a dependency of a task it does not define.
                step("publishable-package contents");
                turbo(&["pack:check", NOT_DOCS], offline)
            }
            Self::Coverage => {
                step("coverage (rust lcov + python xml + js)");
                turbo(&["coverage", NOT_DOCS], offline)
            }
        }
    }
}

/// Every stage, in the order the whole gate runs them.
///
/// Order is deliberate: the cheap repo-wide lints fail in seconds, the format
/// gate fails before any compile, and only then does turbo fan out the package
/// suites. Coverage is last because it is the most expensive producer and its
/// artifacts are only interesting once everything else is green.
pub const STAGES: &[Stage] = &[Stage::Repo, Stage::Lint, Stage::Test, Stage::Coverage];

/// The whole gate's steps, in order — the list the stages must partition.
pub const GATE_STEPS: &[&str] = &[
    "repo lints",
    "format drift gate",
    "package lints",
    "tests",
    "publishable-package contents",
    "coverage",
];

/// Run the whole gate, or one stage of it.
///
/// `coverage` is honoured only for the whole gate: a caller that asked for
/// `--stage coverage` means it, and silently doing nothing would be a green
/// run that proved nothing.
///
/// # Errors
///
/// Propagates the first failing stage, with the step named.
pub fn gate(coverage: bool, offline: bool, stage: Option<Stage>) -> Result<()> {
    if let Some(stage) = stage {
        stage.run(offline)?;
        step(&format!("stage {} passed", stage.name()));
        return Ok(());
    }

    for stage in STAGES {
        if *stage == Stage::Coverage && !coverage {
            continue;
        }
        stage.run(offline)?;
    }

    step("gate passed");
    Ok(())
}

/// Fan one task out across the workspace with turbo, in the `bun` environment.
fn turbo(args: &[&str], offline: bool) -> Result<()> {
    let mut command = vec!["bun", "x", "turbo", "run"];
    command.extend_from_slice(args);
    if offline {
        // Turbo's strict mode removes undeclared variables before package
        // scripts; loose mode is what lets napi's Cargo inherit offline mode.
        command.push("--env-mode=loose");
        pixi_with_env("bun", command, "CARGO_NET_OFFLINE", "true")
    } else {
        pixi("bun", command)
    }
}

/// Fail if the formatters rewrote anything.
///
/// Running the formatter and then checking the tree is deliberate: it tells a
/// contributor *what* to commit, where a `--check` flag would only tell them
/// that something was wrong.
fn assert_no_drift() -> Result<()> {
    let diff = capture("git", ["diff", "--exit-code", "--quiet"])?;
    if diff.status.success() {
        return Ok(());
    }
    let stat = capture("git", ["--no-pager", "diff", "--stat"])?;
    eprint!("{}", String::from_utf8_lossy(&stat.stdout));
    bail!("unformatted files — run `bun x turbo run format` and commit the result");
}

/// Lines that name a cause, rather than the thousands that name a passing test.
/// Public for `tests/ci.rs`: which lines of a failed gate log name a cause is
/// the whole content of the failure summary.
pub const INTERESTING: &[&str] = &[
    "FAILED",
    "error:",
    "ERROR",
    "Error:",
    "assert ",
    "panicked",
    "ImportError",
    "ModuleNotFound",
    "native extension:",
    "package resolved from:",
    "not properly formatted",
    "unformatted files",
    "Failed:",
];

/// Turn a failed gate log into something a reviewer can read without opening
/// the UI: the interesting lines land in the job summary AND in a GitHub
/// annotation, which is the only part of a run the REST API hands back in full.
pub fn failure_summary(log: &str) -> Result<()> {
    let path = repo_root().join(log);
    let path = if path.exists() {
        path
    } else {
        Path::new(log).to_path_buf()
    };
    let text = fs::read_to_string(&path)
        .with_context(|| format!("cannot read gate log {}", path.display()))?;

    let interesting: Vec<&str> = text
        .lines()
        .filter(|line| INTERESTING.iter().any(|needle| line.contains(needle)))
        .collect();
    let tail: Vec<&str> = text.lines().rev().take(200).collect::<Vec<_>>();
    let tail: Vec<&str> = tail.into_iter().rev().collect();

    let summary = format!(
        "### CI gate failed\n\n#### Lines that name a cause\n```\n{}\n```\n\n#### Last 200 lines\n```\n{}\n```\n",
        last(&interesting, 80).join("\n"),
        tail.join("\n"),
    );
    match std::env::var("GITHUB_STEP_SUMMARY") {
        Ok(file) => {
            let mut handle = fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&file)
                .with_context(|| format!("cannot append to {file}"))?;
            handle.write_all(summary.as_bytes())?;
        }
        Err(_) => print!("{summary}"),
    }

    // One annotation, newline-encoded per the workflow-command format.
    let mut annotation: Vec<&str> = last(&interesting, 60);
    annotation.push("--- tail ---");
    annotation.extend(last(&tail, 60));
    let encoded = annotation
        .iter()
        .map(|line| line.replace('%', "%25").replace('\r', "%0D"))
        .collect::<Vec<_>>()
        .join("%0A");
    println!("::error title=CI gate failed::{encoded}%0A");
    Ok(())
}

/// The last `count` entries, in order.
pub fn last<'a>(lines: &[&'a str], count: usize) -> Vec<&'a str> {
    let start = lines.len().saturating_sub(count);
    lines[start..].to_vec()
}

/// Re-exported for `release`, which runs the same turbo fan-out.
pub fn turbo_run(args: &[&str]) -> Result<()> {
    turbo(args, false)
}

/// `cargo` under the QGIS environment, for the release pipeline.
pub fn cargo(args: &[&str]) -> Result<()> {
    let mut command = vec!["cargo"];
    command.extend_from_slice(args);
    pixi("default", command)
}

/// A bare program at the repository root, for callers that need no pixi.
pub fn plain(program: &str, args: &[&str]) -> Result<()> {
    run(program, args)
}
