//! Discovery at the actual process boundary, with no helper runtimes on PATH.
use serde_json::Value;
use std::process::{Command, Output};

fn run(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_qgis-cli"))
        .args(args)
        .env("PATH", "")
        .env("QT_QPA_PLATFORM", "offscreen")
        .output()
        .expect("run CLI directly")
}

#[test]
fn version_reports_the_engine_transport_and_target_without_changing_the_old_flag() {
    let output = run(&["version", "--json"]);
    assert!(output.status.success(), "{:?}", output);
    #[cfg(not(feature = "qgis"))]
    assert!(output.stderr.is_empty(), "{:?}", output);
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["cli"]["version"], env!("CARGO_PKG_VERSION"));
    assert_eq!(report["engine"]["engine"], "qgis-engine");
    assert_eq!(report["engine"]["transport_version"], 1);
    assert!(report["target"]["os"].is_string());
    assert!(report["target"]["arch"].is_string());
    let old = run(&["--version"]);
    assert_eq!(
        String::from_utf8(old.stdout).unwrap(),
        format!("qgis-cli {}\n", env!("CARGO_PKG_VERSION"))
    );
}

#[test]
fn capabilities_are_deterministic_and_separate_commands_from_engine_operations() {
    let output = run(&["capabilities", "--json"]);
    assert!(output.status.success(), "{output:?}");
    assert_eq!(output.stdout, run(&["capabilities", "--json"]).stdout);
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    let commands = report["commands"].as_array().unwrap();
    assert!(commands.contains(&serde_json::json!("info")));
    assert!(commands.contains(&serde_json::json!("validate")));
    assert!(commands.contains(&serde_json::json!("inspect")));
    assert!(commands.contains(&serde_json::json!("plan")));
    assert!(report["command_note"]
        .as_str()
        .unwrap()
        .contains("not availability"));
    let help = run(&["--help"]);
    assert!(help.status.success());
    assert!(String::from_utf8_lossy(&help.stdout).contains("inspect"));
    assert!(String::from_utf8_lossy(&help.stdout).contains("plan"));
    let plan_help = run(&["plan", "--help"]);
    assert!(plan_help.status.success());
    let plan_commands = String::from_utf8(plan_help.stdout).unwrap();
    assert!(plan_commands.contains("tiles"));
    assert!(plan_commands.contains("batch"));
    let ops = report["engine"]["operations"].as_array().unwrap();
    assert!(!ops.iter().any(|op| op["name"] == "inspect"));
    // `plan tiles` is CLI arithmetic over qgis-render, so it adds no engine
    // operation of its own — `plan_tiles` already existed before this command.
    assert!(!ops.iter().any(|op| op["name"] == "plan"));
    assert!(!ops.iter().any(|op| op["name"] == "plan_batch"));
    assert!(ops
        .iter()
        .any(|op| op["name"] == "plan_tiles" && op["available"] == true));
    assert!(ops
        .iter()
        .any(|op| op["name"] == "project_layers" && op["available"] == false));
}

#[test]
fn doctor_reports_optional_backend_absence_as_healthy_pure_operation() {
    let output = run(&["doctor", "--json"]);
    assert!(output.status.success(), "{output:?}");
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["status"], "healthy");
    assert!(report["diagnosis"].as_str().unwrap().contains("optional"));
    #[cfg(not(feature = "qgis"))]
    {
        assert!(output.stderr.is_empty());
        assert_eq!(report["engine"]["backend"]["available"], false);
    }
    let human = run(&["doctor"]);
    assert!(human.status.success());
    let text = String::from_utf8(human.stdout).unwrap();
    assert!(text.contains("healthy"));
    assert!(text.contains("QGIS backend"));
    let invalid = run(&["doctor", "--unknown"]);
    assert_eq!(invalid.status.code(), Some(2));
    assert!(invalid.stdout.is_empty());
    assert!(!invalid.stderr.is_empty());
}
