//! Validation through argv, output streams, and process status, without helper runtimes.
use serde_json::{json, Value};
use std::process::{Command, Output};

fn run(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_qgis-cli"))
        .args(args)
        .env("PATH", "")
        .env("QT_QPA_PLATFORM", "offscreen")
        .output()
        .expect("run CLI")
}

fn validate(kind: &str, value: &str) -> Output {
    run(&["validate", "--json", kind, "--", value])
}

#[test]
fn extent_validation_returns_normalized_coordinates_without_diagnostics() {
    let output = validate("extent", " 14, 50, 15, 51 ");
    assert_eq!(output.status.code(), Some(0), "{output:?}");
    assert!(output.stderr.is_empty(), "{output:?}");
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(
        report,
        json!({
            "kind": "extent", "valid": true,
            "value": {"min_x": 14.0, "min_y": 50.0, "max_x": 15.0, "max_y": 51.0},
            "error": null
        })
    );
    assert_eq!(output.stdout, validate("extent", " 14, 50, 15, 51 ").stdout);
}

#[test]
fn invalid_extents_report_domain_errors_with_exit_ten_and_json_only_stdout() {
    for input in [
        "15,50,14,51",
        "14,51,15,50",
        "NaN,0,1,1",
        "0,0,inf,1",
        "0,0,1",
        "",
        "é,0,1,1",
    ] {
        let output = validate("extent", input);
        assert_eq!(output.status.code(), Some(10), "{input}: {output:?}");
        let report: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(report["kind"], "extent");
        assert_eq!(report["valid"], false);
        assert!(report["value"].is_null());
        assert_eq!(report["error"]["code"], "invalid_input");
        let message = report["error"]["message"].as_str().unwrap();
        assert!(String::from_utf8_lossy(&output.stderr).contains(message));
        assert_eq!(output.stdout, validate("extent", input).stdout);
    }
}

#[test]
fn zero_area_and_negative_extents_keep_the_existing_domain_semantics() {
    for input in ["0,0,0,0", "-180,-90,180,90", "-1,2,-1,3"] {
        let output = validate("extent", input);
        assert_eq!(output.status.code(), Some(0), "{output:?}");
        assert!(output.stderr.is_empty());
    }
}

#[test]
fn crs_validation_normalizes_syntax_without_claiming_database_recognition() {
    for (input, expected) in [
        (" epsg:4326 ", "EPSG:4326"),
        ("custom:999999", "CUSTOM:999999"),
    ] {
        let output = validate("crs", input);
        assert_eq!(output.status.code(), Some(0), "{output:?}");
        assert!(output.stderr.is_empty());
        let report: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(
            report,
            json!({"kind": "crs", "valid": true, "value": {
            "auth_id": expected, "validation": "syntax_only"
        }, "error": null})
        );
    }
    for input in [
        "",
        "EPSG",
        ":4326",
        "EPSG:",
        "EPSG:foo",
        "EPSG:4326:0",
        "ÉPSG:4326",
    ] {
        let output = validate("crs", input);
        assert_eq!(output.status.code(), Some(10), "{output:?}");
        let report: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(report["error"]["code"], "invalid_input");
    }
}

#[test]
fn zoom_validation_preserves_inclusive_ranges_and_enforces_the_domain_limit() {
    for (input, expected) in [
        (" 10 - 14 ", json!({"min": 10, "max": 14})),
        ("0", json!({"min": 0, "max": 0})),
        ("22", json!({"min": 22, "max": 22})),
    ] {
        let output = validate("zoom", input);
        assert_eq!(output.status.code(), Some(0), "{output:?}");
        let report: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(
            report,
            json!({"kind": "zoom", "valid": true, "value": expected, "error": null})
        );
    }
    for input in [
        "23",
        "14-10",
        "-1",
        "0-23",
        "4294967296",
        "1-2-3",
        "NaN",
        "",
    ] {
        let output = validate("zoom", input);
        assert_eq!(output.status.code(), Some(10), "{input}: {output:?}");
        let report: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(report["valid"], false);
    }
}

#[test]
fn tile_validation_checks_xyz_before_returning_geographic_bounds() {
    let output = validate("tile", " 10 / 551 / 342 ");
    assert_eq!(output.status.code(), Some(0), "{output:?}");
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["kind"], "tile");
    assert_eq!(
        report["value"]["tile"],
        json!({"z": 10, "x": 551, "y": 342})
    );
    assert_eq!(report["value"]["bounds"]["min_x"], 13.710_937_5);
    assert_eq!(report["value"]["bounds"]["max_x"], 14.0625);
    assert!(
        (report["value"]["bounds"]["max_y"].as_f64().unwrap() - 51.179_342_979_289_27).abs()
            < 1e-12
    );
    for input in ["0/0/0", "22/4194303/4194303", "10/551/340"] {
        assert_eq!(validate("tile", input).status.code(), Some(0));
    }
    for input in [
        "",
        "0/0",
        "0/0/0/0",
        "0/1/0",
        "0/0/1",
        "23/0/0",
        "32/0/0",
        "4294967295/0/0",
        "10/4294967295/0",
        "10/0/4294967295",
        "4294967296/0/0",
        "-1/0/0",
        "1/NaN/0",
        "22/4194304/0",
    ] {
        let output = validate("tile", input);
        assert_eq!(output.status.code(), Some(10), "{input}: {output:?}");
        let report: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(report["valid"], false);
        assert!(report["value"].is_null());
        assert_eq!(report["error"]["code"], "invalid_input");
    }
}

#[test]
fn validation_usage_errors_remain_exit_two_with_no_json_on_stdout() {
    for args in [
        vec!["validate"],
        vec!["validate", "extent"],
        vec!["validate", "extent", "--json"],
        vec!["validate", "unknown", "0"],
        vec!["validate", "zoom", "0", "--unknown"],
        vec!["validate", "zoom", "0", "extra"],
    ] {
        let output = run(&args);
        assert_eq!(output.status.code(), Some(2), "{args:?}: {output:?}");
        assert!(output.stdout.is_empty());
        assert!(!output.stderr.is_empty());
    }
}

#[test]
fn approved_command_spelling_accepts_json_after_the_value() {
    for (kind, value) in [
        ("extent", "14,50,15,51"),
        ("crs", "epsg:4326"),
        ("zoom", "10-14"),
        ("tile", "10/551/340"),
    ] {
        let output = run(&["validate", kind, value, "--json"]);
        assert_eq!(output.status.code(), Some(0), "{output:?}");
        assert!(output.stderr.is_empty());
        assert_eq!(output.stdout, validate(kind, value).stdout);
    }
}

#[test]
fn human_output_separates_success_from_domain_diagnostics() {
    let good = run(&["validate", "crs", "epsg:4326"]);
    assert_eq!(good.status.code(), Some(0));
    assert!(good.stderr.is_empty());
    let text = String::from_utf8(good.stdout).unwrap();
    assert!(text.contains("valid crs"));
    assert!(text.contains("EPSG:4326"));
    assert!(text.contains("syntax_only"));
    let bad = run(&["validate", "zoom", "23"]);
    assert_eq!(bad.status.code(), Some(10));
    assert!(bad.stdout.is_empty());
    assert!(String::from_utf8_lossy(&bad.stderr).contains("invalid zoom range"));
}

#[test]
fn legacy_execution_errors_keep_exit_one() {
    let output = run(&["info", "/definitely/not/here.qgs"]);
    assert_eq!(output.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&output.stderr).contains("project not found"));
}

#[test]
fn validation_does_not_write_artifacts_or_user_configuration() {
    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let dir = std::env::temp_dir().join(format!("qgis-validate-{}-{unique}", std::process::id()));
    std::fs::create_dir(&dir).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_qgis-cli"))
        .args(["validate", "tile", "0/0/0", "--json"])
        .current_dir(&dir)
        .env("HOME", &dir)
        .env("XDG_CONFIG_HOME", &dir)
        .env("PATH", "")
        .env("QT_QPA_PLATFORM", "offscreen")
        .output()
        .expect("run validator");
    let entries = std::fs::read_dir(&dir).unwrap().count();
    std::fs::remove_dir_all(&dir).unwrap();
    assert_eq!(output.status.code(), Some(0), "{output:?}");
    assert!(output.stderr.is_empty());
    assert_eq!(entries, 0);
}
