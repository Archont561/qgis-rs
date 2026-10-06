//! The gate's two pure helpers: the log tail, and the filter that decides
//! which lines of a failed run name a cause worth putting in the summary.

use std::collections::HashSet;

use xtask::ci::{last, Stage, GATE_STEPS, INTERESTING, REPO_LINTS, STAGES};

/// The split into CI lanes must not change what the gate does.
///
/// A workflow that runs `--stage repo`, `--stage lint` and `--stage test` on
/// three runners is only equivalent to `pixi run ci` if the stages are a
/// *partition* of the gate: concatenating them in order reproduces the whole
/// list, so no step is dropped (green CI that checked less) and none appears
/// twice (a step paid for on two runners).
#[test]
fn the_stages_partition_the_gate_in_order() {
    let concatenated: Vec<&str> = STAGES
        .iter()
        .flat_map(|stage| stage.steps().iter().copied())
        .collect();

    assert_eq!(concatenated, GATE_STEPS);
}

#[test]
fn no_step_belongs_to_two_stages() {
    let mut seen = HashSet::new();
    for stage in STAGES {
        for step in stage.steps() {
            assert!(
                seen.insert(*step),
                "{step} is claimed by more than one stage"
            );
        }
    }
}

#[test]
fn every_stage_is_named_for_the_flag_that_selects_it() {
    assert_eq!(
        STAGES.iter().map(|stage| stage.name()).collect::<Vec<_>>(),
        ["repo", "lint", "test", "coverage"]
    );
    // The cheap lane is first and carries the checks that need no compiler:
    // that ordering is why a format violation can fail in under a minute.
    assert_eq!(Stage::Repo.steps(), ["repo lints", "format drift gate"]);
    // Coverage is last and alone, so a lane can skip it without reaching into
    // another stage's list.
    assert_eq!(Stage::Coverage.steps(), ["coverage"]);
}

#[test]
fn repo_lints_check_generated_api_before_any_compile() {
    assert_eq!(
        REPO_LINTS
            .iter()
            .map(|lint| lint.name())
            .collect::<Vec<_>>(),
        [
            "check-sources",
            "check-boundaries",
            "api-manifest --check",
            "validate-bridge-fixtures",
            "check-protocol-docs",
            "check-api-operations"
        ]
    );
}

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
