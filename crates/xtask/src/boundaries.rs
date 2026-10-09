//! The product boundaries of D13, checked against the manifests that would
//! break them.
//!
//! [D13](../../../.knowledge/decisions/D13-rust-cli-ffi-and-qgis-sdk-boundaries.md)
//! and [doc-7] say four things a manifest can contradict: the hosted SDK does
//! not depend on the standalone engine's binding crate, the binding crates own
//! no process semantics, each canonical executable has exactly one owner, and
//! a fallback is a second set of answers rather than a convenience.
//!
//! A decision record cannot enforce itself. Every one of those four is a fact
//! about `Cargo.toml`, `pyproject.toml` and which files exist, so this module
//! reads them and the gate fails when one stops being true. What it cannot
//! check is also worth naming: whether the *behaviour* behind a binary matches
//! its contract is a test in that package, not a manifest lint.
//!
//! [doc-7]: ../../../backlog/docs/architecture/doc-7%20-%20Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md

use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};

/// A crate manifest reduced to the three facts the contract has an opinion
/// about. Public because `tests/boundaries.rs` builds these by hand: the rules
/// are worth testing against a manifest that does *not* exist in this tree.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CrateFacts {
    /// `[package] name`.
    pub name: String,
    /// Every key in a dependency table, in declaration order.
    pub dependencies: Vec<String>,
    /// Every `[[bin]] name`.
    pub binaries: Vec<String>,
}

/// A Python distribution reduced the same way.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct DistributionFacts {
    /// `[project] name`.
    pub name: String,
    /// `[project] dependencies`, as written.
    pub dependencies: Vec<String>,
}

/// Everything the four rules are decided from. Public for the same reason as
/// [`CrateFacts`]: a violation has to be expressible in a test.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Tree {
    /// One entry per `crates/*/Cargo.toml`.
    pub crates: Vec<CrateFacts>,
    /// One entry per `py-packages/*/pyproject.toml`.
    pub distributions: Vec<DistributionFacts>,
    /// Repository-relative paths of files whose name contains `fallback`.
    pub fallbacks: Vec<String>,
}

/// Dependency edges the contract forbids: `(crate, must not depend on, why)`.
///
/// Only *direct* edges are listed, because that is what the rule is about —
/// `qgis-sdk` reaching `qgis-engine` through `qgis-cli` is the sanctioned reuse
/// path (D13 §3), while naming `qgis-py` would couple two Python extensions
/// built for two different interpreters.
pub const FORBIDDEN_EDGES: &[(&str, &str, &str)] = &[(
    "qgis-sdk",
    "qgis-py",
    "D13 §3: the hosted SDK must not load the standalone engine's extension; \
     share Rust through qgis-protocol/qgis-engine instead",
)];

/// Crates that exist only to carry the wire protocol into another language.
///
/// D13 §4 keeps process semantics — argv, exit codes, signals — in the
/// canonical Rust binaries, so a binding crate that grows a `[[bin]]` is also
/// the bug that made two crates fight over `target/<profile>/qgis-cli`.
pub const BINDING_CRATES: &[&str] = &["qgis-py", "qgis-node"];

/// `(executable, the one crate allowed to declare it)` — D13 §1 and §4.
pub const CANONICAL_BINARIES: &[(&str, &str)] =
    &[("qgis-cli", "qgis-cli"), ("qgis-sdk", "qgis-sdk")];

/// Repository automation executables. They are not product commands, so they
/// need no D13 owner: `xtask` is the only one, and it is never shipped.
pub const TOOLING_BINARIES: &[&str] = &["xtask"];

/// Fallback modules that exist today, each with the task that removes it.
///
/// The no-fallback policy (D09, D13 §4) is about *new* ones: an allowlist
/// turns the survivors into something a reader can count and a task can close,
/// where a silent exception is how a second set of answers survives a rewrite.
pub const TRACKED_FALLBACKS: &[(&str, &str)] = &[(
    "py-packages/qgis-sdk/src/qgis_sdk/_fallback_cli.py",
    "TASK-43 removes it with the hosted-runtime split; qgis_sdk.cli imports it \
     when qgis_sdk._core is missing",
)];

/// One broken rule, named the way the gate prints it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Violation {
    /// Which of the four rules broke.
    pub rule: &'static str,
    /// What was found, and what the contract says instead.
    pub detail: String,
}

/// Check the boundaries against the repository at `root`.
///
/// # Errors
///
/// Fails when a manifest is unreadable, or when any rule is violated — with
/// every violation listed, because fixing them one gate run at a time is how a
/// contract check becomes something people stop running.
pub fn check(root: &Path) -> Result<()> {
    let tree = read_tree(root)?;
    let violations = violations(&tree);
    if violations.is_empty() {
        println!(
            "check-boundaries: {} crates and {} distributions match D13 ({} tracked fallback(s))",
            tree.crates.len(),
            tree.distributions.len(),
            TRACKED_FALLBACKS.len()
        );
        return Ok(());
    }
    for violation in &violations {
        eprintln!(
            "boundary violation [{}]: {}",
            violation.rule, violation.detail
        );
    }
    bail!(
        "{} product-boundary violation(s) — see .knowledge/decisions/D13-rust-cli-ffi-and-qgis-sdk-boundaries.md",
        violations.len()
    );
}

/// Apply the four rules to an already-read tree.
///
/// Pure, and public, so a test can hand it a manifest this repository does not
/// contain — which is the only way to prove the rules actually fail.
#[must_use]
pub fn violations(tree: &Tree) -> Vec<Violation> {
    let mut found = Vec::new();

    for (crate_name, forbidden, why) in FORBIDDEN_EDGES {
        if let Some(facts) = tree.crates.iter().find(|facts| facts.name == *crate_name) {
            if facts.dependencies.iter().any(|name| name == forbidden) {
                found.push(Violation {
                    rule: "dependency direction",
                    detail: format!("{crate_name} depends on {forbidden} — {why}"),
                });
            }
        }
    }

    for binding in BINDING_CRATES {
        if let Some(facts) = tree.crates.iter().find(|facts| facts.name == *binding) {
            for binary in &facts.binaries {
                found.push(Violation {
                    rule: "binding crates own no binaries",
                    detail: format!(
                        "{binding} declares [[bin]] {binary} — D13 §4 keeps argv, exit codes \
                         and signals in the canonical Rust binaries"
                    ),
                });
            }
        }
    }

    for (binary, owner) in CANONICAL_BINARIES {
        let declaring: Vec<&str> = tree
            .crates
            .iter()
            .filter(|facts| facts.binaries.iter().any(|name| name == binary))
            .map(|facts| facts.name.as_str())
            .collect();
        match declaring.as_slice() {
            [] => found.push(Violation {
                rule: "canonical executables",
                detail: format!("no crate declares {binary}; D13 §1 gives it to {owner}"),
            }),
            [only] if only == owner => {}
            several => found.push(Violation {
                rule: "canonical executables",
                detail: format!(
                    "{binary} is declared by {} — D13 §1 gives it to {owner} alone, and cargo \
                     resolves every bin to the same target/<profile>/{binary}",
                    several.join(", ")
                ),
            }),
        }
    }

    for facts in &tree.crates {
        for binary in &facts.binaries {
            if !CANONICAL_BINARIES.iter().any(|(name, _)| name == binary)
                && !TOOLING_BINARIES.contains(&binary.as_str())
            {
                found.push(Violation {
                    rule: "canonical executables",
                    detail: format!(
                        "{binary} is declared by {} but is not a canonical executable; \
                         qgis-plugin was dropped and qgis-sdk is the only plugin command (D13 §1)",
                        facts.name
                    ),
                });
            }
        }
    }

    for path in &tree.fallbacks {
        if !TRACKED_FALLBACKS.iter().any(|(tracked, _)| tracked == path) {
            found.push(Violation {
                rule: "no new fallbacks",
                detail: format!(
                    "{path} is an untracked fallback — D09 and D13 §4 forbid a second set of \
                     answers; add it to TRACKED_FALLBACKS with the task that removes it, or delete it"
                ),
            });
        }
    }

    for (tracked, _) in TRACKED_FALLBACKS {
        if !tree.fallbacks.iter().any(|path| path == tracked) {
            found.push(Violation {
                rule: "no new fallbacks",
                detail: format!(
                    "{tracked} is allowlisted but gone — delete the entry, the exception it \
                     documents has been paid off"
                ),
            });
        }
    }

    found
}

/// Read the manifests and the fallback inventory out of a repository tree.
///
/// # Errors
///
/// Fails when a manifest directory cannot be listed or a manifest cannot be
/// read. A missing `crates/` is an error too: a check that silently finds
/// nothing passes forever.
pub fn read_tree(root: &Path) -> Result<Tree> {
    let mut crates = Vec::new();
    for manifest in manifests(&root.join("crates"), "Cargo.toml")? {
        let text = std::fs::read_to_string(&manifest)
            .with_context(|| format!("cannot read {}", manifest.display()))?;
        crates.push(parse_crate(&text));
    }
    for directory in crate::util::RUST_CRATE_ROOTS {
        let manifest = root.join(directory).join("Cargo.toml");
        let text = std::fs::read_to_string(&manifest)
            .with_context(|| format!("cannot read {}", manifest.display()))?;
        crates.push(parse_crate(&text));
    }
    crates.sort_by(|left, right| left.name.cmp(&right.name));

    let mut distributions = Vec::new();
    for manifest in manifests(&root.join("py-packages"), "pyproject.toml")? {
        let text = std::fs::read_to_string(&manifest)
            .with_context(|| format!("cannot read {}", manifest.display()))?;
        distributions.push(parse_distribution(&text));
    }
    distributions.sort_by(|left, right| left.name.cmp(&right.name));

    let mut fallbacks = Vec::new();
    for tree in ["py-packages", "ts-packages", "crates"] {
        for entry in walkdir::WalkDir::new(root.join(tree))
            .into_iter()
            .filter_entry(|entry| entry.file_name() != "node_modules")
            .filter_map(std::result::Result::ok)
            .filter(|entry| entry.file_type().is_file())
        {
            let name = entry.file_name().to_string_lossy().to_lowercase();
            if name.contains("fallback") {
                let path = entry
                    .path()
                    .strip_prefix(root)
                    .unwrap_or(entry.path())
                    .to_string_lossy()
                    .into_owned();
                fallbacks.push(path);
            }
        }
    }
    fallbacks.sort();

    Ok(Tree {
        crates,
        distributions,
        fallbacks,
    })
}

/// Every `<directory>/*/<file_name>`, sorted.
fn manifests(directory: &Path, file_name: &str) -> Result<Vec<PathBuf>> {
    let entries = std::fs::read_dir(directory)
        .with_context(|| format!("cannot list {}", directory.display()))?;
    let mut found: Vec<PathBuf> = entries
        .filter_map(std::result::Result::ok)
        .map(|entry| entry.path().join(file_name))
        .filter(|path| path.is_file())
        .collect();
    found.sort();
    Ok(found)
}

/// Pull `[package] name`, the dependency keys and the `[[bin]]` names out of a
/// Cargo manifest.
///
/// A hand-rolled scanner rather than a TOML parser: the three facts live in
/// `key = value` lines directly under a known table header, xtask's dependency
/// list is deliberately four crates long, and a lint that needs a new
/// dependency to run is a lint that cannot run on an airlocked machine.
/// Public because the parser is what `tests/boundaries.rs` pins down.
#[must_use]
pub fn parse_crate(text: &str) -> CrateFacts {
    let mut facts = CrateFacts::default();
    let mut section = String::new();
    for line in text.lines() {
        let line = strip_comment(line);
        if line.is_empty() {
            continue;
        }
        if let Some(header) = table_header(line) {
            if header == "[[bin]]" {
                facts.binaries.push(String::new());
            }
            section = header.to_string();
            continue;
        }
        let Some((key, value)) = key_value(line) else {
            continue;
        };
        match section.as_str() {
            "[package]" if key == "name" => facts.name = unquote(value).to_string(),
            "[[bin]]" if key == "name" => {
                if let Some(last) = facts.binaries.last_mut() {
                    *last = unquote(value).to_string();
                }
            }
            section if is_dependency_table(section) => facts.dependencies.push(key.to_string()),
            _ => {}
        }
    }
    facts.binaries.retain(|name| !name.is_empty());
    facts
}

/// Pull `[project] name` and `[project] dependencies` out of a pyproject.
///
/// Public for the tests, like [`parse_crate`].
#[must_use]
pub fn parse_distribution(text: &str) -> DistributionFacts {
    let mut facts = DistributionFacts::default();
    let mut section = String::new();
    let mut in_dependencies = false;
    for line in text.lines() {
        let line = strip_comment(line);
        if line.is_empty() {
            continue;
        }
        if let Some(header) = table_header(line) {
            section = header.to_string();
            in_dependencies = false;
            continue;
        }
        if section != "[project]" {
            continue;
        }
        if in_dependencies {
            if line.starts_with(']') {
                in_dependencies = false;
                continue;
            }
            facts
                .dependencies
                .push(unquote(line.trim_end_matches(',')).to_string());
            continue;
        }
        let Some((key, value)) = key_value(line) else {
            continue;
        };
        match key {
            "name" => facts.name = unquote(value).to_string(),
            "dependencies" => {
                let inline = value.trim_start_matches('[').trim_end_matches(']');
                if value.ends_with(']') {
                    facts.dependencies.extend(
                        inline
                            .split(',')
                            .map(str::trim)
                            .filter(|item| !item.is_empty())
                            .map(|item| unquote(item).to_string()),
                    );
                } else {
                    in_dependencies = true;
                }
            }
            _ => {}
        }
    }
    facts
}

/// The three tables whose keys are dependency names.
fn is_dependency_table(section: &str) -> bool {
    matches!(
        section,
        "[dependencies]" | "[dev-dependencies]" | "[build-dependencies]"
    ) || section.ends_with(".dependencies]")
}

/// `[table]` or `[[array]]` at the start of a line.
fn table_header(line: &str) -> Option<&str> {
    line.starts_with('[').then_some(line)
}

/// Split `key = value`, with the key unquoted and both sides trimmed.
fn key_value(line: &str) -> Option<(&str, &str)> {
    let (key, value) = line.split_once('=')?;
    Some((unquote(key.trim()), value.trim()))
}

/// Drop a trailing `# comment` and surrounding whitespace.
fn strip_comment(line: &str) -> &str {
    let line = line.trim();
    if line.starts_with('#') {
        return "";
    }
    line
}

/// Remove one layer of single or double quotes.
fn unquote(value: &str) -> &str {
    value
        .trim()
        .trim_matches('"')
        .trim_matches('\'')
        .split_whitespace()
        .next()
        .unwrap_or("")
}
