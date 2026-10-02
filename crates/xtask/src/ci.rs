//! The gate, and what to print when it fails.
//!
//! `pixi run xtask ci` locally and the CI workflow run exactly this function,
//! so "passes on my machine" and "passes in Actions" cannot mean different
//! things.

use std::fs;
use std::io::Write;
use std::path::Path;

use anyhow::{bail, Context, Result};

use crate::util::{capture, pixi, repo_root, run, step};

/// The docs site is excluded from every fan-out below: it is built and
/// deployed by docs.yml, and pulling Astro into the gate would double the
/// critical path for a surface that cannot break the libraries.
const NOT_DOCS: &str = "--filter=!qgis-rs-docs";

/// Run the whole gate.
///
/// Order is deliberate: the cheap repo-wide lints fail in seconds, the format
/// gate fails before any compile, and only then does turbo fan out the package
/// suites. Coverage runs last because it is the most expensive producer and
/// its artifacts are only interesting once everything else is green.
pub fn gate(coverage: bool) -> Result<()> {
    step("repo lints (taplo, actionlint)");
    pixi("default", ["xtask", "lint-toml"])?;
    pixi("default", ["actionlint"])?;

    step("package lints (turbo fan-out)");
    turbo(&["lint", NOT_DOCS])?;

    step("format drift gate");
    turbo(&["format", NOT_DOCS])?;
    assert_no_drift()?;

    step("tests (turbo fan-out; each package builds what it needs)");
    turbo(&["test", NOT_DOCS])?;

    step("publishable-package contents");
    turbo(&["pack:check"])?;

    if coverage {
        step("coverage (rust lcov + python xml + js)");
        turbo(&["coverage", NOT_DOCS])?;
    }

    step("gate passed");
    Ok(())
}

/// Fan one task out across the workspace with turbo, in the `bun` environment.
fn turbo(args: &[&str]) -> Result<()> {
    let mut command = vec!["bun", "x", "turbo", "run"];
    command.extend_from_slice(args);
    pixi("bun", command)
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
const INTERESTING: &[&str] = &[
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
fn last<'a>(lines: &[&'a str], count: usize) -> Vec<&'a str> {
    let start = lines.len().saturating_sub(count);
    lines[start..].to_vec()
}

/// Re-exported for `release`, which runs the same turbo fan-out.
pub fn turbo_run(args: &[&str]) -> Result<()> {
    turbo(args)
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_tail_helper_keeps_order_and_bounds() {
        let lines = ["one", "two", "three"];
        assert_eq!(last(&lines, 2), ["two", "three"]);
        assert_eq!(last(&lines, 9), ["one", "two", "three"]);
        assert!(last(&[], 5).is_empty());
    }

    #[test]
    fn the_interesting_filter_finds_causes_not_passes() {
        let log = "test foo ... ok\nerror: cannot find value\nrunning 3 tests\nFAILED bar\n";
        let found: Vec<&str> = log
            .lines()
            .filter(|line| INTERESTING.iter().any(|needle| line.contains(needle)))
            .collect();
        assert_eq!(found, ["error: cannot find value", "FAILED bar"]);
    }
}
