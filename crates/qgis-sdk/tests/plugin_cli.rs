//! Integration tests for the Rust-native `qgis-plugin` executable.
//!
//! Plugin command behavior belongs to the Rust crate; Python tests separately
//! smoke-test the installed package and its PyO3 boundary.
//!
//! The five free functions this file used to open with (`run`, `temp_dir`,
//! `stdout`, `stderr`, `failure`) are now one `plugin` fixture returning a
//! [`PluginCli`]: a scratch directory plus a way to invoke the binary against
//! it. Both pieces of hard-won knowledge survive the move — the directory name
//! is still unique per run, and a failed child still reports its exit status
//! and both streams on one line.

use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicUsize, Ordering};

use rstest::{fixture, rstest};

const QGIS_PLUGIN: &str = env!("CARGO_BIN_EXE_qgis-plugin");

/// One `qgis-plugin` invocation, already decoded.
struct Run {
    command: String,
    status: std::process::ExitStatus,
    stdout: String,
    stderr: String,
}

impl Run {
    fn succeeded(&self) -> bool {
        self.status.success()
    }

    /// One line that says everything about a child that did not exit 0.
    ///
    /// `assert!(status.success(), "{stderr}")` was not enough: a process
    /// killed by a signal writes nothing, so CI reported a panic with a blank
    /// message and the cause had to be guessed. The exit status carries the
    /// signal on Unix, and both streams are folded onto one line because the
    /// gate forwards single lines into the job annotation.
    fn failure(&self) -> String {
        let flatten = |text: &str| text.replace('\n', " ⏎ ");
        format!(
            "error: `qgis-plugin {}` exited with {:?} — stderr: {} | stdout: {}",
            self.command,
            self.status,
            flatten(&self.stderr),
            flatten(&self.stdout),
        )
    }
}

/// The executable under test, plus a scratch directory of its own.
struct PluginCli {
    dir: PathBuf,
}

impl PluginCli {
    /// A directory no other run of this suite can be holding.
    ///
    /// `pid` plus a counter is not enough: the gate runs this binary twice in
    /// one container — once under `turbo run test`, once under
    /// `cargo llvm-cov` — and a runner recycles process ids freely. A leftover
    /// directory from a run that died before `Drop` makes `qgis-plugin new`
    /// bail with "directory already exists", which is how this test went red
    /// in CI on a commit that changed only prose. The clock closes that
    /// window; the explicit removal closes what is left of it.
    fn new() -> Self {
        static NEXT_ID: AtomicUsize = AtomicUsize::new(0);
        let id = NEXT_ID.fetch_add(1, Ordering::Relaxed);
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |since| since.as_nanos());
        let dir = std::env::temp_dir().join(format!(
            "qgis-sdk-plugin-cli-{}-{id}-{stamp}",
            std::process::id()
        ));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).expect("create temporary directory");
        Self { dir }
    }

    fn path(&self) -> &Path {
        &self.dir
    }

    fn run(&self, args: &[&str]) -> Run {
        let output = Command::new(QGIS_PLUGIN)
            .args(args)
            .output()
            .unwrap_or_else(|error| panic!("run `qgis-plugin {}`: {error}", args.join(" ")));
        Run {
            command: args.join(" "),
            status: output.status,
            stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
            stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
        }
    }
}

impl Drop for PluginCli {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.dir);
    }
}

#[fixture]
fn plugin() -> PluginCli {
    PluginCli::new()
}

#[rstest]
#[case("new")]
#[case("validate")]
#[case("info")]
#[case("version")]
fn help_lists_every_subcommand(plugin: PluginCli, #[case] command: &str) {
    let run = plugin.run(&["--help"]);
    assert!(run.succeeded(), "{}", run.failure());
    assert!(
        run.stdout.contains(command),
        "{command} missing from: {}",
        run.stdout
    );
}

#[rstest]
fn version_reports_the_crate_version(plugin: PluginCli) {
    let run = plugin.run(&["version"]);
    assert!(run.succeeded(), "{}", run.failure());
    assert!(run
        .stdout
        .contains(&format!("qgis-plugin {}", env!("CARGO_PKG_VERSION"))));
}

#[rstest]
fn scaffolds_validates_and_reports_a_plugin(plugin: PluginCli) {
    let into = plugin.path().to_str().expect("utf-8");
    let run = plugin.run(&["new", "smoke_plugin", "--type", "general", "-o", into]);
    assert!(run.succeeded(), "{}", run.failure());

    let scaffolded = plugin.path().join("smoke_plugin");
    assert!(scaffolded.join("metadata.txt").is_file());
    assert!(scaffolded.join("smoke_plugin/__init__.py").is_file());

    let scaffolded = scaffolded.to_str().expect("utf-8");

    let run = plugin.run(&["validate", scaffolded]);
    assert!(run.succeeded(), "{}", run.failure());
    assert!(run.stdout.contains("looks valid"));

    let run = plugin.run(&["info", scaffolded, "--json"]);
    assert!(run.succeeded(), "{}", run.failure());
    let info: serde_json::Value = serde_json::from_str(&run.stdout).expect("valid JSON");
    assert_eq!(info["name"], "smoke_plugin");
    assert_eq!(info["version"], "0.1.0");
}
