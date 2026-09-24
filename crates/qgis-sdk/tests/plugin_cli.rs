//! Integration tests for the Rust-native `qgis-plugin` executable.
//!
//! Plugin command behavior belongs to the Rust crate; Python tests separately
//! smoke-test the installed package and its PyO3 boundary.

use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicUsize, Ordering};

const QGIS_PLUGIN: &str = env!("CARGO_BIN_EXE_qgis-plugin");

fn run(args: &[&str]) -> Output {
    Command::new(QGIS_PLUGIN)
        .args(args)
        .output()
        .unwrap_or_else(|error| panic!("run `qgis-plugin {}`: {error}", args.join(" ")))
}

fn temp_dir() -> TempDir {
    static NEXT_ID: AtomicUsize = AtomicUsize::new(0);
    let id = NEXT_ID.fetch_add(1, Ordering::Relaxed);
    let path =
        std::env::temp_dir().join(format!("qgis-sdk-plugin-cli-{}-{id}", std::process::id()));
    std::fs::create_dir_all(&path).expect("create temporary directory");
    TempDir(path)
}

struct TempDir(PathBuf);

impl TempDir {
    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn stdout(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

#[test]
fn help_and_version_are_available() {
    let output = run(&["--help"]);
    assert!(output.status.success(), "{}", stderr(&output));
    let help = stdout(&output);
    for command in ["new", "validate", "info", "version"] {
        assert!(help.contains(command), "{command} missing from: {help}");
    }

    let output = run(&["version"]);
    assert!(output.status.success(), "{}", stderr(&output));
    assert!(stdout(&output).contains(&format!("qgis-plugin {}", env!("CARGO_PKG_VERSION"))));
}

#[test]
fn scaffolds_validates_and_reports_a_plugin() {
    let temp = temp_dir();
    let output = Command::new(QGIS_PLUGIN)
        .args(["new", "smoke_plugin", "--type", "general", "-o"])
        .arg(temp.path())
        .output()
        .expect("run `qgis-plugin new`");
    assert!(output.status.success(), "{}", stderr(&output));

    let plugin = temp.path().join("smoke_plugin");
    assert!(plugin.join("metadata.txt").is_file());
    assert!(plugin.join("smoke_plugin/__init__.py").is_file());

    let output = Command::new(QGIS_PLUGIN)
        .arg("validate")
        .arg(&plugin)
        .output()
        .expect("run `qgis-plugin validate`");
    assert!(output.status.success(), "{}", stderr(&output));
    assert!(stdout(&output).contains("looks valid"));

    let output = Command::new(QGIS_PLUGIN)
        .arg("info")
        .arg(&plugin)
        .arg("--json")
        .output()
        .expect("run `qgis-plugin info`");
    assert!(output.status.success(), "{}", stderr(&output));
    let info: serde_json::Value = serde_json::from_slice(&output.stdout).expect("valid JSON");
    assert_eq!(info["name"], "smoke_plugin");
    assert_eq!(info["version"], "0.1.0");
}
