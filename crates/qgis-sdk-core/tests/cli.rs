//! Behaviour of the shared plugin command line, driven through `run_cli`.
//!
//! These tests call the library the way the `qgis-sdk` and `qgis-sdk`
//! binaries and the `qgis_sdk._core` extension do: argv in, exit code out, and
//! filesystem effects checked on disk. The binaries' own process behaviour is
//! covered in `crates/qgis-sdk/tests/plugin_cli.rs`.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

use qgis_sdk_core::run_cli;

/// A scratch directory that is removed when the test ends, even on failure.
struct Scratch(PathBuf);

impl Scratch {
    fn new() -> Self {
        static NEXT_ID: AtomicUsize = AtomicUsize::new(0);
        let id = NEXT_ID.fetch_add(1, Ordering::Relaxed);
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |since| since.as_nanos());
        let path =
            std::env::temp_dir().join(format!("qgis-sdk-core-{}-{stamp}-{id}", std::process::id()));
        std::fs::create_dir_all(&path).expect("create scratch directory");
        Self(path)
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

#[test]
fn asking_for_help_or_version_exits_zero() {
    // Given the program name and a request for help
    // When the shared parser handles it
    // Then clap prints the text and the exit code is 0
    assert_eq!(run_cli(["qgis-sdk", "--help"]), 0);
    assert_eq!(run_cli(["qgis-sdk", "--version"]), 0);
}

#[test]
fn an_unknown_command_is_a_usage_error_with_clap_exit_code_two() {
    // Given an argv naming a command that does not exist
    // When the shared parser runs it
    // Then the exit code is clap's usage-error code, 2
    assert_eq!(run_cli(["qgis-sdk", "no-such-command"]), 2);
}

#[test]
fn scaffolding_into_a_fresh_directory_creates_the_plugin_and_exits_zero() {
    // Given an empty output directory
    let scratch = Scratch::new();
    let output = scratch.path().display().to_string();

    // When a plugin named `demo_plugin` is scaffolded into it
    let code = run_cli(["qgis-sdk", "new", "demo_plugin", "--output", &output]);

    // Then the command succeeds and the plugin directory exists
    assert_eq!(code, 0);
    assert!(scratch.path().join("demo_plugin").is_dir());
}

#[test]
fn scaffolding_over_an_existing_directory_fails_and_leaves_it_untouched() {
    // Given a directory that already holds a file of the same name
    let scratch = Scratch::new();
    let existing = scratch.path().join("demo_plugin");
    std::fs::create_dir_all(&existing).expect("create existing plugin directory");
    let sentinel = existing.join("keep.txt");
    std::fs::write(&sentinel, "mine").expect("write sentinel");
    let output = scratch.path().display().to_string();

    // When the same plugin is scaffolded again
    let code = run_cli(["qgis-sdk", "new", "demo_plugin", "--output", &output]);

    // Then the command fails and the existing file is still there, unchanged
    assert_eq!(code, 1);
    assert_eq!(
        std::fs::read_to_string(&sentinel).expect("sentinel survives"),
        "mine"
    );
}

#[test]
fn validating_a_directory_with_no_plugin_fails_and_writes_nothing() {
    // Given an empty directory that is not a plugin
    let scratch = Scratch::new();
    let target = scratch.path().display().to_string();

    // When it is validated
    let code = run_cli(["qgis-sdk", "validate", &target]);

    // Then validation fails with exit code 1 and creates no files
    assert_eq!(code, 1);
    let entries = std::fs::read_dir(scratch.path())
        .expect("read scratch")
        .count();
    assert_eq!(
        entries, 0,
        "validate must not write into the directory it checks"
    );
}
