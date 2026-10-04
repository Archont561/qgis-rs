//! The command tree: clap's own consistency check, plus the two argument
//! shapes other tools depend on — the gate's single flag, and the staged file
//! list lefthook appends to `check-cpp`.

use clap::{CommandFactory, Parser};
use xtask::{Cli, Command};

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
fn long_help_lists_every_repository_verb() {
    let mut command = Cli::command();
    let help = command.render_long_help().to_string();
    for verb in [
        "ci",
        "check-cpp",
        "format-cpp",
        "clang-tidy",
        "check-sources",
        "check-boundaries",
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
