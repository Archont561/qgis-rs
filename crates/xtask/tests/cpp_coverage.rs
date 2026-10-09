//! Native coverage is useful only when the report contains executed production
//! code. These consumer-side tests pin fail-closed validation of gcovr reports.

use xtask::cpp_coverage::validate_summary;

#[test]
fn native_coverage_accepts_executed_manager_and_enforces_conversions_floor() {
    let report = r#"{"files":[
        {"filename":"crates/qgis-sys/src/native_manager/conversions.cpp","line_total":40,"line_covered":38},
        {"filename":"crates/qgis-sys/src/native_manager/manager.cpp","line_total":100,"line_covered":70}
    ]}"#;
    validate_summary(report).expect("95 percent conversions and an executed manager");

    let below = report.replace("\"line_covered\":38", "\"line_covered\":37");
    let error = validate_summary(&below).unwrap_err().to_string();
    assert!(error.contains("conversions.cpp"), "{error}");
    assert!(error.contains("95"), "{error}");
}

#[test]
fn coverage_command_is_discoverable_without_running_a_compiler() {
    use clap::Parser;
    let parsed = xtask::Cli::try_parse_from(["xtask", "cpp-coverage"]);
    assert!(parsed.is_ok(), "{parsed:?}");
    use clap::CommandFactory;
    let help = xtask::Cli::command().render_long_help().to_string();
    assert!(help.contains("pixi run xtask cpp-coverage"), "{help}");
}

#[test]
fn missing_empty_duplicate_and_invalid_production_rows_fail_closed() {
    for report in [
        r#"{"files":[]}"#,
        r#"{"files":[{"filename":"crates/qgis-sys/src/native_manager/conversions.cpp","line_total":0,"line_covered":0}]}"#,
        r#"{"files":[{"filename":"crates/qgis-sys/src/native_manager/conversions.cpp","line_total":10,"line_covered":11}]}"#,
        "not json",
    ] {
        assert!(validate_summary(report).is_err(), "{report}");
    }
}

#[test]
fn a_complete_conversions_report_cannot_hide_missing_or_unexecuted_manager() {
    let conversions = r#"{"filename":"crates/qgis-sys/src/native_manager/conversions.cpp","line_total":100,"line_covered":95}"#;
    for manager in [
        "",
        r#",{"filename":"crates/qgis-sys/src/native_manager/manager.cpp","line_total":100,"line_covered":0}"#,
        r#",{"filename":"crates/qgis-sys/src/native_manager/manager.cpp","line_total":100,"line_covered":101}"#,
        r#",{"filename":"crates/qgis-sys/src/native_manager/manager.cpp","line_total":100,"line_covered":1},{"filename":"crates/qgis-sys/src/native_manager/manager.cpp","line_total":100,"line_covered":1}"#,
    ] {
        let json = format!("{{\"files\":[{conversions}{manager}]}}");
        assert!(validate_summary(&json).is_err(), "{json}");
    }
}

#[test]
fn native_tests_are_offline_serial_and_instrumented_without_touching_normal_cache() {
    use std::{collections::BTreeMap, ffi::OsStr, path::Path};
    let command = xtask::cpp_coverage::native_test_command(Path::new("/scratch/repo"));
    assert_eq!(command.get_program(), "cargo");
    assert_eq!(command.get_current_dir(), Some(Path::new("/scratch/repo")));
    let args: Vec<_> = command.get_args().collect();
    assert!(args.contains(&OsStr::new("--offline")));
    assert!(args.contains(&OsStr::new("--test-threads=1")));
    assert!(args.contains(&OsStr::new("qgis-sys/qgis,qgis-mcp/qgis")));
    let env: BTreeMap<_, _> = command.get_envs().collect();
    assert_eq!(
        env[OsStr::new("CARGO_TARGET_DIR")],
        Some(OsStr::new("/scratch/repo/target/cpp-coverage/cargo"))
    );
    assert_eq!(
        env[OsStr::new("QT_QPA_PLATFORM")],
        Some(OsStr::new("offscreen"))
    );
    assert_eq!(env[OsStr::new("CXX")], Some(OsStr::new("g++")));
    assert_eq!(
        env[OsStr::new("CXXFLAGS")],
        Some(OsStr::new("--coverage -O0 -g -fprofile-update=atomic"))
    );
    assert_eq!(
        env[OsStr::new("RUSTFLAGS")],
        Some(OsStr::new("-C link-arg=-lgcov"))
    );
}
