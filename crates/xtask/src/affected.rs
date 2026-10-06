//! Plan the smallest safe local check set for the current Git changes.

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command as ProcessCommand;

use anyhow::{bail, Context, Result};

use crate::util;

/// A test ownership boundary selected by a changed path.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum Scope {
    /// A Cargo package, tested together with all reverse dependencies.
    Rust(String),
    /// A Turbo workspace package, selected together with downstream packages.
    Package(String),
}

/// One subprocess in an affected plan.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlannedCommand {
    pub program: String,
    pub args: Vec<String>,
}

impl PlannedCommand {
    /// Shell-like rendering for dry-run output (not evaluated by a shell).
    #[must_use]
    pub fn display(&self) -> String {
        format!("{} {}", self.program, self.args.join(" "))
    }
}

/// Deterministic affected-test plan.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Plan {
    pub changed: Vec<PathBuf>,
    pub scopes: Vec<Scope>,
    pub commands: Vec<PlannedCommand>,
    pub full_gate: bool,
}

/// Convert changed repository-relative paths into a safe test plan.
pub fn plan(root: &Path, changed: &[PathBuf], force: bool) -> Result<Plan> {
    let mut changed = changed.to_vec();
    changed.sort();
    changed.dedup();
    let mut scopes = BTreeSet::new();
    let mut full_gate = false;

    for path in &changed {
        let text = path.to_string_lossy().replace('\\', "/");
        if is_global(&text) {
            full_gate = true;
            break;
        }
        if let Some((kind, directory)) = owner(&text) {
            let manifest = root.join(directory).join(if kind == "crates" {
                "Cargo.toml"
            } else {
                "package.json"
            });
            let name = manifest_name(&manifest, kind == "crates")?;
            scopes.insert(if kind == "crates" {
                Scope::Rust(name)
            } else {
                Scope::Package(name)
            });
        } else {
            // Unknown top-level inputs are safer as a full gate than as no work.
            full_gate = true;
            break;
        }
    }

    let scopes: Vec<_> = if full_gate {
        Vec::new()
    } else {
        scopes.into_iter().collect()
    };
    let commands = commands(&scopes, full_gate, force);
    Ok(Plan {
        changed,
        scopes,
        commands,
        full_gate,
    })
}

fn is_global(path: &str) -> bool {
    matches!(
        path,
        "Cargo.toml"
            | "Cargo.lock"
            | "bun.lock"
            | "pixi.toml"
            | "pixi.lock"
            | "turbo.json"
            | "package.json"
            | "lefthook.yml"
    ) || path.starts_with("test-fixtures/")
        || path.starts_with(".github/")
        || path.starts_with("scripts/")
        || path.starts_with("crates/xtask/")
}

fn owner(path: &str) -> Option<(&str, PathBuf)> {
    let mut parts = path.split('/');
    let kind = parts.next()?;
    if !matches!(kind, "crates" | "ts-packages" | "py-packages" | "docs") {
        return None;
    }
    if kind == "docs" {
        return Some((kind, PathBuf::from("docs")));
    }
    let package = parts.next()?;
    Some((kind, PathBuf::from(kind).join(package)))
}

fn manifest_name(path: &Path, cargo: bool) -> Result<String> {
    let body = fs::read_to_string(path)
        .with_context(|| format!("cannot read owner manifest {}", path.display()))?;
    if cargo {
        let mut in_package = false;
        for line in body.lines() {
            let line = line.trim();
            if line.starts_with('[') {
                in_package = line == "[package]";
            } else if in_package && line.starts_with("name") {
                return quoted_value(line).context("package name is not quoted");
            }
        }
        bail!("{} has no [package] name", path.display());
    }
    let value: serde_json::Value = serde_json::from_str(&body)?;
    value["name"]
        .as_str()
        .map(str::to_owned)
        .with_context(|| format!("{} has no string name", path.display()))
}

fn quoted_value(line: &str) -> Option<String> {
    let value = line.split_once('=')?.1.trim();
    Some(value.strip_prefix('"')?.strip_suffix('"')?.to_owned())
}

fn commands(scopes: &[Scope], full_gate: bool, force: bool) -> Vec<PlannedCommand> {
    if full_gate {
        return vec![PlannedCommand {
            program: "pixi".into(),
            args: vec!["run".into(), "gates".into()],
        }];
    }
    scopes
        .iter()
        .map(|scope| match scope {
            Scope::Rust(name) => PlannedCommand {
                program: "pixi".into(),
                args: vec![
                    "run".into(),
                    "--".into(),
                    "cargo".into(),
                    "nextest".into(),
                    "run".into(),
                    "-E".into(),
                    format!("rdeps({name})"),
                ],
            },
            Scope::Package(name) => {
                let mut args = vec![
                    "run".into(),
                    "--".into(),
                    "bun".into(),
                    "x".into(),
                    "turbo".into(),
                    "run".into(),
                    "lint".into(),
                    "test".into(),
                    format!("--filter={name}..."),
                ];
                if force {
                    args.push("--force".into());
                }
                PlannedCommand {
                    program: "pixi".into(),
                    args,
                }
            }
        })
        .collect()
}

/// Discover committed, staged, unstaged and untracked paths relative to `base`.
pub fn changed_paths(root: &Path, base: Option<&str>) -> Result<Vec<PathBuf>> {
    let base = match base {
        Some(base) => base.to_owned(),
        None => git_text(root, &["merge-base", "HEAD", "origin/main"])?
            .trim()
            .to_owned(),
    };
    let mut paths = BTreeSet::new();
    let committed = format!("{base}...HEAD");
    for args in [
        vec!["diff", "--name-only", "-z", committed.as_str()],
        vec!["diff", "--name-only", "-z"],
        vec!["diff", "--cached", "--name-only", "-z"],
        vec!["ls-files", "--others", "--exclude-standard", "-z"],
    ] {
        for path in git_bytes(root, &args)?
            .split(|byte| *byte == 0)
            .filter(|p| !p.is_empty())
        {
            paths.insert(PathBuf::from(String::from_utf8_lossy(path).into_owned()));
        }
    }
    Ok(paths.into_iter().collect())
}

fn git_text(root: &Path, args: &[&str]) -> Result<String> {
    Ok(String::from_utf8(git_bytes(root, args)?)?)
}

fn git_bytes(root: &Path, args: &[&str]) -> Result<Vec<u8>> {
    let output = ProcessCommand::new("git")
        .args(args)
        .current_dir(root)
        .output()?;
    if !output.status.success() {
        bail!(
            "git {} failed: {}",
            args.join(" "),
            String::from_utf8_lossy(&output.stderr)
        );
    }
    Ok(output.stdout)
}

/// Print the plan and, unless `dry_run`, execute it without a shell.
pub fn run(base: Option<&str>, dry_run: bool, force: bool) -> Result<()> {
    let root = util::repo_root();
    let changed = changed_paths(&root, base)?;
    let plan = plan(&root, &changed, force)?;
    if plan.commands.is_empty() {
        println!("No affected checks: working tree and base diff are clean.");
        return Ok(());
    }
    println!("Changed paths: {}", plan.changed.len());
    for command in &plan.commands {
        println!("{}", command.display());
        if !dry_run {
            util::run_in(&root, &command.program, &command.args)?;
        }
    }
    Ok(())
}
