//! The command tree: clap's own consistency check, plus the two argument
//! shapes other tools depend on — the gate's single flag, and the staged file
//! list lefthook appends to `check-cpp`.

use clap::{CommandFactory, Parser};
use xtask::ci::Stage;
use xtask::{Cli, Command};

#[test]
fn the_command_tree_is_well_formed() {
    Cli::command().debug_assert();
}

#[test]
fn the_gate_accepts_fast_and_offline_modes() {
    let cli = Cli::try_parse_from(["xtask", "ci", "--no-coverage", "--offline"]).expect("parses");
    assert!(matches!(
        cli.command,
        Command::Ci {
            no_coverage: true,
            offline: true,
            stage: None,
        }
    ));
}

/// Every CI lane is one of these spellings, so a typo in `ci.yml` fails at
/// argument parsing rather than by quietly running a different stage.
#[test]
fn the_gate_accepts_one_stage_at_a_time() {
    for (flag, expected) in [
        ("repo", Stage::Repo),
        ("lint", Stage::Lint),
        ("test", Stage::Test),
        ("coverage", Stage::Coverage),
    ] {
        let cli = Cli::try_parse_from(["xtask", "ci", "--stage", flag]).expect("parses");
        let Command::Ci { stage, .. } = cli.command else {
            panic!("--stage {flag} did not parse as the ci subcommand");
        };
        assert_eq!(stage, Some(expected));
    }

    assert!(Cli::try_parse_from(["xtask", "ci", "--stage", "lints"]).is_err());
}

#[test]
fn long_help_lists_every_repository_verb() {
    let mut command = Cli::command();
    let help = command.render_long_help().to_string();
    for verb in [
        "affected",
        "ci",
        "check-cpp",
        "format-cpp",
        "clang-tidy",
        "check-sources",
        "check-boundaries",
        "check-protocol-docs",
        "lint-toml",
        "pack-check",
        "setup-qca",
        "ci-failure-summary",
        "api-manifest",
        "scaffold",
        "release",
    ] {
        assert!(help.contains(verb), "long help omitted {verb}");
    }
}

#[test]
fn affected_accepts_a_base_and_non_executing_modes() {
    let cli = Cli::try_parse_from([
        "xtask",
        "affected",
        "--base",
        "HEAD~2",
        "--dry-run",
        "--force",
    ])
    .expect("parses");
    assert!(matches!(
        cli.command,
        Command::Affected {
            base: Some(ref base),
            dry_run: true,
            force: true,
        } if base == "HEAD~2"
    ));
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
