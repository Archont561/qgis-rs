//! Repository automation for qgis-rs.
//!
//! One binary behind one pixi task: `pixi run xtask <subcommand>`. A workflow
//! step, a lefthook hook and a developer all run the same command, and adding
//! a verb means adding a subcommand here rather than another file in a
//! `scripts/` directory that four manifests have to know the path of.
//!
//! What is deliberately NOT here: the per-package build/test/lint verbs. Those
//! live in each package's own `package.json` and are orchestrated by turbo, so
//! the command that builds the Python wheel is in the manifest a reader of
//! that package already opens. xtask owns the work that is genuinely
//! repository-wide — the gate, the repo lints, the scaffolder, the release
//! pipeline — plus the one environment repair a fresh QGIS prefix needs.
//!
//! See `.knowledge/decisions/D10-xtask-over-shell-scripts.md`.
//!
//! # Why a library and not just `main.rs`
//!
//! The tests live in `tests/`, next to the source rather than inside it, and
//! an integration test can only reach a *library*. So the command tree and the
//! modules behind it are this crate's public surface and `src/main.rs` is six
//! lines of dispatch. Nothing outside the repository depends on that surface —
//! the crate is `publish = false` — but the tests are a consumer like any
//! other, and a consumer is exactly what the public API is for.

pub mod ci;
pub mod lints;
pub mod release;
pub mod scaffold;
pub mod util;

use anyhow::Result;
use clap::{Parser, Subcommand};

/// Every repository-wide verb qgis-rs has, as clap sees it.
#[derive(Debug, Parser)]
#[command(
    name = "xtask",
    about = "Repository automation for qgis-rs",
    long_about = "Every repository-wide verb qgis-rs has. Run through pixi:\n  \
                  pixi run xtask ci\n  \
                  pixi run xtask check-cpp [files...]\n  \
                  pixi run xtask format-cpp\n  \
                  pixi run xtask clang-tidy\n  \
                  pixi run xtask release verify-version v1.2.3",
    version
)]
pub struct Cli {
    /// The subcommand to run.
    #[command(subcommand)]
    pub command: Command,
}

/// The subcommands, one per repository-wide verb.
#[derive(Debug, Subcommand)]
pub enum Command {
    /// The whole gate: repo lints, turbo lint/format/test/pack:check, coverage.
    Ci {
        /// Skip the coverage producers — the fast pre-push loop.
        #[arg(long)]
        no_coverage: bool,
    },
    /// clang-format gate for the C++ shim (given files, or the whole tree).
    CheckCpp {
        /// Files to check; with none, every .cpp/.h under crates/qgis-sys.
        files: Vec<String>,
    },
    /// Write clang-format's output over the C++ shim.
    FormatCpp,
    /// clang-tidy over the C++ shim, discovering the include paths it needs.
    ClangTidy,
    /// Fail if a source file inside a package tree is hidden by .gitignore.
    CheckSources,
    /// taplo canonicality check for the manifests kept in canonical form.
    LintToml {
        /// Files to check; with none, pixi.toml.
        files: Vec<String>,
    },
    /// Assert a package directory contains everything its `files` list promises.
    PackCheck {
        /// The package directory, relative to the repository root.
        package_dir: String,
        /// Entries that must exist. A trailing `/` means a directory; `*` globs.
        required: Vec<String>,
    },
    /// Link libqca under the Qt5 soname QGIS still asks for.
    SetupQca,
    /// Turn a failed gate log into a GitHub job summary and an annotation.
    CiFailureSummary {
        /// The captured gate log.
        log: String,
    },
    /// Scaffold a qgis-sys binding: header + cxx bridge + C++ shim + wiring.
    Scaffold {
        /// Layer directory, e.g. `core`.
        layer: String,
        /// Concept directory, e.g. `geometry`.
        concept: String,
        /// The QGIS class being bound, e.g. `QgsGeometry`.
        qgis_class: String,
        /// Short module name, e.g. `geometry`.
        short_name: String,
    },
    /// The release pipeline, step by step.
    #[command(subcommand)]
    Release(release::Release),
}

/// Run one parsed command.
///
/// # Errors
///
/// Propagates whatever the subcommand failed at, with the step named.
pub fn run(command: Command) -> Result<()> {
    match command {
        Command::Ci { no_coverage } => ci::gate(!no_coverage),
        Command::CheckCpp { files } => lints::check_cpp(&files),
        Command::FormatCpp => lints::format_cpp(),
        Command::ClangTidy => lints::clang_tidy(),
        Command::CheckSources => lints::check_sources(),
        Command::LintToml { files } => lints::lint_toml(&files),
        Command::PackCheck {
            package_dir,
            required,
        } => lints::pack_check(&package_dir, &required),
        Command::SetupQca => lints::setup_qca(),
        Command::CiFailureSummary { log } => ci::failure_summary(&log),
        Command::Scaffold {
            layer,
            concept,
            qgis_class,
            short_name,
        } => scaffold::binding(&layer, &concept, &qgis_class, &short_name),
        Command::Release(step) => release::run(step),
    }
}
