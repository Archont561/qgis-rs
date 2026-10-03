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

/// A directory no other run of this suite can be holding.
///
/// `pid` plus a counter is not enough: the gate runs this binary twice in one
/// container — once under `turbo run test`, once under `cargo llvm-cov` — and
/// a runner recycles process ids freely. A leftover directory from a run that
/// died before `Drop` makes `qgis-plugin new` bail with "directory already
/// exists", which is how this test went red in CI on a commit that changed
/// only prose. The clock closes that window; the explicit removal closes what
/// is left of it.
fn temp_dir() -> TempDir {
    static NEXT_ID: AtomicUsize = AtomicUsize::new(0);
    let id = NEXT_ID.fetch_add(1, Ordering::Relaxed);
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |since| since.as_nanos());
    let path = std::env::temp_dir().join(format!(
        "qgis-sdk-plugin-cli-{}-{id}-{stamp}",
        std::process::id()
    ));
    let _ = std::fs::remove_dir_all(&path);
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

/// One line that says everything about a child that did not exit 0.
///
/// `assert!(status.success(), "{}", stderr(&output))` was not enough: a
/// process killed by a signal writes nothing, so CI reported a panic with a
/// blank message and the cause had to be guessed. The exit status carries the
/// signal on Unix, and both streams are folded onto one line because the gate
/// forwards single lines into the job annotation.
fn failure(command: &str, output: &Output) -> String {
    let flatten = |text: String| text.replace('\n', " ⏎ ");
    format!(
        "error: `qgis-plugin {command}` exited with {:?} — stderr: {} | stdout: {}",
        output.status,
        flatten(stderr(output)),
        flatten(stdout(output)),
    )
}

#[test]
fn help_and_version_are_available() {
    let output = run(&["--help"]);
    assert!(output.status.success(), "{}", failure("--help", &output));
    let help = stdout(&output);
    for command in ["new", "validate", "info", "version"] {
        assert!(help.contains(command), "{command} missing from: {help}");
    }

    let output = run(&["version"]);
    assert!(output.status.success(), "{}", failure("version", &output));
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
    assert!(output.status.success(), "{}", failure("new", &output));

    let plugin = temp.path().join("smoke_plugin");
    assert!(plugin.join("metadata.txt").is_file());
    assert!(plugin.join("smoke_plugin/__init__.py").is_file());

    let output = Command::new(QGIS_PLUGIN)
        .arg("validate")
        .arg(&plugin)
        .output()
        .expect("run `qgis-plugin validate`");
    assert!(output.status.success(), "{}", failure("validate", &output));
    assert!(stdout(&output).contains("looks valid"));

    let output = Command::new(QGIS_PLUGIN)
        .arg("info")
        .arg(&plugin)
        .arg("--json")
        .output()
        .expect("run `qgis-plugin info`");
    assert!(output.status.success(), "{}", failure("info", &output));
    let info: serde_json::Value = serde_json::from_slice(&output.stdout).expect("valid JSON");
    assert_eq!(info["name"], "smoke_plugin");
    assert_eq!(info["version"], "0.1.0");
}
