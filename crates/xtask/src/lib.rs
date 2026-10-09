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

pub mod affected;
pub mod api_extract;
pub mod api_manifest;
pub mod boundaries;
pub mod bridge_fixtures;
pub mod ci;
pub mod cpp;
pub mod cpp_coverage;
pub mod lints;
pub mod protocol_docs;
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
                  pixi run xtask ci [--no-coverage] [--offline] [--stage STAGE]\n  \
                  pixi run xtask affected [--base REF] [--dry-run] [--force]\n  \
                  pixi run xtask check-cpp [files...]\n  \
                  pixi run xtask test-cpp\n  \
                  pixi run xtask cpp-coverage\n  \
                  pixi run xtask format-cpp\n  \
                  pixi run xtask clang-tidy\n  \
                  pixi run xtask check-sources\n  \
                  pixi run xtask check-boundaries\n  \
                  pixi run xtask validate-bridge-fixtures\n  \
                  pixi run xtask check-protocol-docs\n  \
                  pixi run xtask check-api-operations\n  \
                  pixi run xtask lint-toml [files...]\n  \
                  pixi run xtask pack-check <package-dir> <required...>\n  \
                  pixi run xtask setup-qca\n  \
                  pixi run xtask ci-failure-summary <log>\n  \
                  pixi run xtask api-manifest [--check] [--diff-against PATH]\n  \
                  pixi run xtask api-extract [--check]\n  \
                  pixi run xtask scaffold <operation> <handler>\n  \
                  pixi run xtask release <step>",
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
    /// Plan and run checks affected by local and branch changes.
    Affected {
        /// Compare committed changes with this ref instead of origin/main's merge base.
        #[arg(long, value_name = "REF")]
        base: Option<String>,
        /// Print the deterministic plan without executing it.
        #[arg(long)]
        dry_run: bool,
        /// Ignore Turbo's cache for selected package checks.
        #[arg(long)]
        force: bool,
    },
    /// The whole gate: repo lints, turbo lint/format/test/pack:check, coverage.
    Ci {
        /// Skip the coverage producers — the fast pre-push loop.
        #[arg(long)]
        no_coverage: bool,
        /// Force Cargo subprocesses offline, including those spawned by napi.
        #[arg(long)]
        offline: bool,
        /// Run one slice of the gate instead of all of it — what a CI lane does.
        #[arg(long, value_name = "STAGE")]
        stage: Option<ci::Stage>,
    },
    /// clang-format gate for the native manager (given files, or the whole tree).
    CheckCpp {
        /// Files to check; with none, every .cpp/.h under crates/qgis-sys.
        files: Vec<String>,
    },
    /// Write clang-format's output over the native manager.
    FormatCpp,
    /// Build and run the native manager's GoogleTest/RapidCheck suite.
    TestCpp,
    /// Measure GCC native coverage offline, separately from normal builds.
    CppCoverage,
    /// clang-tidy over the native manager, discovering the include paths it needs.
    ClangTidy,
    /// Fail if a source file inside a package tree is hidden by .gitignore.
    CheckSources,
    /// Fail if a manifest contradicts the D13 product boundaries.
    CheckBoundaries,
    /// Validate the shared Python/TypeScript bridge contract fixtures.
    ValidateBridgeFixtures,
    /// Fail if the wire-protocol reference page drifts from `qgis-protocol`.
    CheckProtocolDocs,
    /// Fail if the API manifest and `qgis-protocol` disagree about operations.
    CheckApiOperations,
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
    /// Validate the versioned QGIS API manifest and generate native-manager fragments.
    ApiManifest {
        /// Check generated fragments without rewriting them.
        #[arg(long)]
        check: bool,
        /// Compare the current manifest against a prior checked-in manifest.
        #[arg(long, value_name = "PATH")]
        diff_against: Option<String>,
    },
    /// Add a reviewable operation to the native-manager API manifest.
    Scaffold {
        /// Snake-case protocol operation name, e.g. `project_save`.
        operation: String,
        /// C++ native-manager handler identifier, e.g. `project_save`.
        handler: String,
    },
    /// Discover the declared headers' public API and write the inventory.
    ///
    /// Without `--check` the checked-in inventory is regenerated; with it the
    /// repository is verified the way the `check-api-inventory` lint does.
    ApiExtract {
        /// Verify the checked-in inventory instead of rewriting it.
        #[arg(long)]
        check: bool,
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
        Command::Affected {
            base,
            dry_run,
            force,
        } => affected::run(base.as_deref(), dry_run, force),
        Command::Ci {
            no_coverage,
            offline,
            stage,
        } => ci::gate(!no_coverage, offline, stage),
        Command::CheckCpp { files } => lints::check_cpp(&files),
        Command::FormatCpp => lints::format_cpp(),
        Command::TestCpp => cpp::test_cpp(),
        Command::CppCoverage => cpp_coverage::run(),
        Command::ClangTidy => lints::clang_tidy(),
        Command::CheckSources => lints::check_sources(),
        Command::CheckBoundaries => boundaries::check(&util::repo_root()),
        Command::ValidateBridgeFixtures => {
            bridge_fixtures::run(&util::repo_root().join("test-fixtures/bridge"))
        }
        Command::CheckProtocolDocs => protocol_docs::run(&util::repo_root()),
        Command::CheckApiOperations => api_manifest::run_wire_operations_check(),
        Command::LintToml { files } => lints::lint_toml(&files),
        Command::PackCheck {
            package_dir,
            required,
        } => lints::pack_check(&package_dir, &required),
        Command::SetupQca => lints::setup_qca(),
        Command::CiFailureSummary { log } => ci::failure_summary(&log),
        Command::ApiManifest {
            check,
            diff_against,
        } => api_manifest::run(check, diff_against.as_deref()),
        Command::ApiExtract { check } => api_extract::run(check),
        Command::Scaffold { operation, handler } => {
            scaffold::repository_operation(&operation, &handler)
        }
        Command::Release(step) => release::run(step),
    }
}
