//! `qgis-cli plan tiles` at the process boundary.
//!
//! Planning is pure geometry, so nothing here needs a project file, the QGIS
//! backend, or a helper runtime on `PATH`. That is the point of the command:
//! a pyramid can be counted from an extent alone, which the legacy
//! `tiles <project> --dry-run` cannot do because it opens the project first.

use std::path::PathBuf;
use std::process::{Command, Output};

use rstest::{fixture, rstest};
use serde_json::Value;

const BINARY: &str = env!("CARGO_BIN_EXE_qgis-cli");

/// An empty scratch directory that removes itself on drop.
///
/// Empty on purpose — every test here asserts that planning a pyramid needs
/// nothing on disk and leaves nothing behind.
struct Scratch(PathBuf);

impl Scratch {
    /// The names still in the directory.
    fn entries(&self) -> Vec<String> {
        let mut names: Vec<String> = std::fs::read_dir(&self.0)
            .expect("scratch exists")
            .map(|entry| {
                entry
                    .expect("readable")
                    .file_name()
                    .to_string_lossy()
                    .into_owned()
            })
            .collect();
        names.sort();
        names
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

#[fixture]
fn scratch() -> Scratch {
    let dir = std::env::temp_dir().join(format!("qgis-cli-plan-tiles-{}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("create scratch");
    Scratch(dir)
}

fn run(scratch: &Scratch, args: &[&str]) -> Output {
    Command::new(BINARY)
        .current_dir(&scratch.0)
        .args(args)
        .env("PATH", "")
        .env("QT_QPA_PLATFORM", "offscreen")
        .output()
        .expect("run the CLI")
}

fn stdout_of(output: &Output) -> String {
    String::from_utf8(output.stdout.clone()).expect("utf-8 stdout")
}

fn stderr_of(output: &Output) -> String {
    String::from_utf8(output.stderr.clone()).expect("utf-8 stderr")
}

/// The pyramid the CLI, the engine and both language clients all document.
const GOLDEN: &[&str] = &["plan", "tiles", "-b", "14,50,15,51", "-z", "10-14"];

#[rstest]
fn a_plan_needs_no_project_file(scratch: Scratch) {
    let output = run(&scratch, GOLDEN);

    assert!(output.status.success(), "{}", stderr_of(&output));
    assert!(stderr_of(&output).is_empty(), "{}", stderr_of(&output));
    assert!(
        stdout_of(&output).contains("4568"),
        "{}",
        stdout_of(&output)
    );
    assert_eq!(scratch.entries(), Vec::<String>::new(), "planning wrote");
}

#[rstest]
fn the_human_report_matches_the_documented_golden(scratch: Scratch) {
    let output = run(&scratch, GOLDEN);
    let stdout = stdout_of(&output);

    for expected in [
        "z=10",
        "x 551..554",
        "y 342..347",
        "24 tiles",
        "4568 tiles across zoom levels 10-14",
    ] {
        assert!(
            stdout.contains(expected),
            "{expected:?} missing from:\n{stdout}"
        );
    }
    assert_eq!(
        stdout.matches("z=").count(),
        5,
        "one row per zoom level:\n{stdout}"
    );
}

#[rstest]
fn json_carries_the_shared_report_keys(scratch: Scratch) {
    let output = run(&scratch, &[GOLDEN, &["--json"]].concat());

    let report: Value = serde_json::from_str(&stdout_of(&output)).expect("one JSON report");

    let mut keys: Vec<&String> = report.as_object().expect("object").keys().collect();
    keys.sort();
    assert_eq!(keys, ["bounds", "levels", "tile_count", "zooms"]);
    assert_eq!(report["tile_count"], serde_json::json!(4568));
    assert_eq!(report["zooms"], serde_json::json!({"min": 10, "max": 14}));
    assert_eq!(report["levels"].as_array().expect("levels").len(), 5);
    assert_eq!(
        report["levels"][0],
        serde_json::json!({
            "zoom": 10,
            "x_min": 551,
            "x_max": 554,
            "y_min": 342,
            "y_max": 347,
            "tile_count": 24
        })
    );
}

/// One shape, three surfaces.
///
/// The CLI, the engine's `plan_tiles` wire operation and the MCP tool used to
/// spell the same answer three ways. Comparing them here is what stops a
/// fourth spelling appearing: a rename now has to be made in `qgis-render`
/// and breaks all three tests at once, instead of drifting silently.
#[rstest]
fn json_is_the_engine_and_mcp_answer(scratch: Scratch) {
    let output = run(&scratch, &[GOLDEN, &["--json"]].concat());
    let from_cli: Value = serde_json::from_str(&stdout_of(&output)).expect("one JSON report");

    let engine = qgis_engine::call(
        qgis_engine::Operation::PlanTiles,
        serde_json::json!({"bounds": "14,50,15,51", "zooms": "10-14"}),
    );
    assert!(engine.ok, "{}", engine.result);

    let from_mcp = serde_json::to_value(
        qgis_mcp::QgisMcpServer::plan_tiles_report("14,50,15,51", "10-14").expect("valid"),
    )
    .expect("serialises");

    assert_eq!(from_cli, engine.result, "CLI and engine disagree");
    assert_eq!(from_cli, from_mcp, "CLI and MCP disagree");
}

#[rstest]
fn planning_is_deterministic(scratch: Scratch) {
    let first = stdout_of(&run(&scratch, &[GOLDEN, &["--json"]].concat()));
    let second = stdout_of(&run(&scratch, &[GOLDEN, &["--json"]].concat()));

    assert_eq!(first, second);
}

#[rstest]
#[case::too_few_bounds(&["-b", "14,50,15", "-z", "10-14"])]
#[case::reversed_bounds(&["-b", "15,51,14,50", "-z", "10-14"])]
#[case::not_a_number(&["-b", "14,50,x,51", "-z", "10-14"])]
#[case::zoom_too_deep(&["-b", "14,50,15,51", "-z", "99"])]
#[case::reversed_zoom(&["-b", "14,50,15,51", "-z", "14-10"])]
#[case::not_a_zoom(&["-b", "14,50,15,51", "-z", "ten"])]
fn malformed_input_exits_ten(scratch: Scratch, #[case] flags: &[&str]) {
    let output = run(&scratch, &[&["plan", "tiles"][..], flags].concat());

    assert_eq!(output.status.code(), Some(10), "{}", stderr_of(&output));
    assert!(
        !stderr_of(&output).is_empty(),
        "the reason belongs on stderr"
    );
}

#[rstest]
#[case::no_bounds(&["plan", "tiles", "-z", "10-14"])]
#[case::no_zoom(&["plan", "tiles", "-b", "14,50,15,51"])]
#[case::no_arguments(&["plan"])]
fn missing_arguments_are_a_usage_error(scratch: Scratch, #[case] args: &[&str]) {
    assert_eq!(run(&scratch, args).status.code(), Some(2));
}

/// `--json` failures keep stdout a parseable report and put the reason on
/// stderr, matching the contract `inspect` and `validate` already follow.
#[rstest]
fn json_failures_stay_parseable_and_keep_diagnostics_off_stdout(scratch: Scratch) {
    let output = run(
        &scratch,
        &["plan", "tiles", "-b", "14,50,15", "-z", "10-14", "--json"],
    );

    assert_eq!(output.status.code(), Some(10));
    let report: Value = serde_json::from_str(&stdout_of(&output)).expect("one JSON report");
    assert_eq!(report["error"]["code"], serde_json::json!("invalid_input"));
    assert!(report["error"]["message"]
        .as_str()
        .expect("message")
        .contains("extent"));
    assert!(!stderr_of(&output).is_empty());
}
