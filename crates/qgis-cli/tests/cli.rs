//! End-to-end tests for the `qgis-cli` binary itself.

use std::path::PathBuf;
use std::process::Command;

const BINARY: &str = env!("CARGO_BIN_EXE_qgis-cli");

/// Run the CLI and capture everything.
fn run(args: &[&str]) -> std::process::Output {
    Command::new(BINARY)
        .args(args)
        .output()
        .unwrap_or_else(|error| panic!("run `qgis-cli {}`: {error}", args.join(" ")))
}

fn temp_dir(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("qgis-cli-it-{name}"));
    std::fs::create_dir_all(&dir).expect("create dir");
    dir
}

fn write_project(dir: &std::path::Path, name: &str) -> PathBuf {
    let path = dir.join(name);
    std::fs::write(&path, b"<qgis></qgis>").expect("write project");
    path
}

fn stdout_of(output: &std::process::Output) -> String {
    String::from_utf8_lossy(&output.stdout).to_string()
}

fn stderr_of(output: &std::process::Output) -> String {
    String::from_utf8_lossy(&output.stderr).to_string()
}

#[test]
fn help_lists_every_subcommand() {
    let output = run(&["--help"]);
    assert!(output.status.success());

    let help = stdout_of(&output);
    for command in ["render", "tiles", "batch", "info", "serve", "export"] {
        assert!(help.contains(command), "{command} missing from: {help}");
    }
}

#[test]
fn a_dry_run_counts_tiles_without_rendering() {
    let dir = temp_dir("dry-run");
    let project = write_project(&dir, "map.qgs");

    let output = run(&[
        "tiles",
        project.to_str().expect("utf-8"),
        "-z",
        "10-14",
        "-b",
        "14,50,15,51",
        "-o",
        dir.join("tiles").to_str().expect("utf-8"),
        "--dry-run",
    ]);
    assert!(output.status.success(), "{}", stderr_of(&output));

    let stdout = stdout_of(&output);
    assert!(stdout.contains("Would render 4568 tiles"), "{stdout}");
    assert!(stdout.contains("z=10"), "{stdout}");
    assert!(stdout.contains("24 tiles"), "{stdout}");
}

#[test]
fn info_prints_json_without_needing_qgis() {
    let dir = temp_dir("info");
    let project = write_project(&dir, "map.qgz");

    let output = run(&["info", project.to_str().expect("utf-8"), "--json"]);
    assert!(output.status.success(), "{}", stderr_of(&output));

    let stdout = stdout_of(&output);
    let parsed: serde_json::Value = serde_json::from_str(&stdout).expect("valid json");
    assert_eq!(parsed["format"], "qgz");
    assert!(parsed["size_bytes"].as_u64().expect("size") > 0);
    assert!(parsed["note"]
        .as_str()
        .expect("note")
        .contains("QGIS backend"));
}

#[test]
fn operations_that_need_qgis_say_so() {
    let dir = temp_dir("unwired");
    let project = write_project(&dir, "map.qgs");
    let target = dir.join("out.png");

    let output = run(&[
        "render",
        project.to_str().expect("utf-8"),
        "-o",
        target.to_str().expect("utf-8"),
    ]);
    assert!(!output.status.success());
    let stderr = stderr_of(&output);
    assert!(stderr.contains("QGIS backend"), "{stderr}");
    assert!(!target.exists(), "nothing should have been written");
}

#[test]
fn a_missing_project_is_reported_with_its_path() {
    let output = run(&["info", "/definitely/not/here.qgs"]);
    assert!(!output.status.success());
    let stderr = stderr_of(&output);
    assert!(stderr.contains("project not found"), "{stderr}");
    assert!(stderr.contains("/definitely/not/here.qgs"), "{stderr}");
}

#[test]
fn serve_needs_a_project_or_a_directory() {
    let output = run(&["serve"]);
    assert!(!output.status.success());
    let stderr = stderr_of(&output);
    assert!(stderr.contains("--projects-dir"), "{stderr}");
}

#[test]
fn batch_reads_the_extents_csv_before_failing() {
    let dir = temp_dir("batch");
    let project = write_project(&dir, "map.qgs");
    let extents = dir.join("extents.csv");
    std::fs::write(
        &extents,
        "name,minx,miny,maxx,maxy\nberlin,13.08,52.33,13.76,52.68\n",
    )
    .expect("write csv");

    let output = run(&[
        "batch",
        project.to_str().expect("utf-8"),
        "--extents",
        extents.to_str().expect("utf-8"),
        "-o",
        dir.join("renders").to_str().expect("utf-8"),
    ]);
    assert!(!output.status.success());

    let stdout = stdout_of(&output);
    assert!(
        stdout.contains("berlin: 13.08,52.33,13.76,52.68"),
        "{stdout}"
    );
    assert!(stderr_of(&output).contains("QGIS backend"));
}

#[test]
fn an_unknown_subcommand_is_a_usage_error() {
    let output = run(&["teleport"]);
    assert!(!output.status.success());
    assert!(stderr_of(&output).contains("unrecognized subcommand"));
}
