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

mod ci;
mod lints;
mod release;
mod scaffold;
mod util;

use anyhow::Result;
use clap::{Parser, Subcommand};

#[derive(Debug, Parser)]
#[command(
    name = "xtask",
    about = "Repository automation for qgis-rs",
    long_about = "Every repository-wide verb qgis-rs has. Run through pixi:\n  \
                  pixi run xtask ci\n  \
                  pixi run xtask check-cpp [files...]\n  \
                  pixi run xtask release verify-version v1.2.3",
    version
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
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
    /// taplo canonicality check for the manifests kept in canonical form.
    LintToml {
        /// Files to check; with none, pixi.toml and pixi-sandbox.toml.
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

fn main() -> Result<()> {
    match Cli::parse().command {
        Command::Ci { no_coverage } => ci::gate(!no_coverage),
        Command::CheckCpp { files } => lints::check_cpp(&files),
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

#[cfg(test)]
mod tests {
    use super::*;
    use clap::CommandFactory;

    #[test]
    fn the_command_tree_is_well_formed() {
        Cli::command().debug_assert();
    }

    #[test]
    fn the_gate_takes_its_one_flag() {
        let cli = Cli::try_parse_from(["xtask", "ci", "--no-coverage"]).expect("parses");
        assert!(matches!(cli.command, Command::Ci { no_coverage: true }));
    }

    #[test]
    fn staged_files_reach_the_lints_as_arguments() {
        // lefthook passes the staged files positionally; a hook that passes
        // none must still mean "check the whole tree", not "check nothing".
        let cli = Cli::try_parse_from(["xtask", "check-cpp", "a.cpp", "b.h"]).expect("parses");
        match cli.command {
            Command::CheckCpp { files } => assert_eq!(files, ["a.cpp", "b.h"]),
            other => panic!("unexpected command: {other:?}"),
        }
        let cli = Cli::try_parse_from(["xtask", "check-cpp"]).expect("parses");
        assert!(matches!(cli.command, Command::CheckCpp { files } if files.is_empty()));
    }
}
