//! Metadata-only inspection through argv, streams, status and filesystem effects.
use std::path::PathBuf;
use std::process::{Command, Output};

use rstest::{fixture, rstest};
use serde_json::{json, Value};

struct Sandbox {
    path: PathBuf,
}

impl Sandbox {
    fn new() -> Self {
        let unique = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path =
            std::env::temp_dir().join(format!("qgis-inspect-{}-{unique}", std::process::id()));
        std::fs::create_dir(&path).unwrap();
        Self { path }
    }

    fn write(&self, name: &str, bytes: &[u8]) {
        std::fs::write(self.path.join(name), bytes).unwrap();
    }

    fn run(&self, args: &[impl AsRef<std::ffi::OsStr>]) -> Output {
        Command::new(env!("CARGO_BIN_EXE_qgis-cli"))
            .args(args)
            .current_dir(&self.path)
            .env("PATH", "")
            .env("HOME", self.path.join("home"))
            .env("XDG_CONFIG_HOME", self.path.join("config"))
            .env("XDG_CACHE_HOME", self.path.join("cache"))
            .env("QT_QPA_PLATFORM", "offscreen")
            .output()
            .expect("run CLI without helper runtimes")
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.path).unwrap();
    }
}

#[fixture]
fn sandbox() -> Sandbox {
    Sandbox::new()
}

#[rstest]
fn inspection_reports_only_file_metadata_in_deterministic_json(sandbox: Sandbox) {
    sandbox.write("map.qgs", b"<qgis/>");
    let output = sandbox.run(&["inspect", "map.qgs", "--json"]);
    assert_eq!(output.status.code(), Some(0), "{output:?}");
    assert!(output.stderr.is_empty(), "{output:?}");
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(
        report,
        json!({
            "inspection": "file_metadata",
            "qgis_validation": "not_performed",
            "value": {"path": "map.qgs", "format": "qgs", "size_bytes": 7},
            "error": null
        })
    );
    assert_eq!(
        output.stdout,
        sandbox.run(&["inspect", "map.qgs", "--json"]).stdout
    );
}

#[rstest]
fn missing_input_has_exit_eleven_and_a_structured_error(sandbox: Sandbox) {
    let output = sandbox.run(&["inspect", "missing.qgs", "--json"]);
    assert_eq!(output.status.code(), Some(11), "{output:?}");
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(
        report,
        json!({
            "inspection": "file_metadata",
            "qgis_validation": "not_performed",
            "value": null,
            "error": {"code": "missing_input", "message": "project file not found: missing.qgs"}
        })
    );
    assert!(String::from_utf8_lossy(&output.stderr).contains("project file not found: missing.qgs"));
    let human = sandbox.run(&["inspect", "missing.qgs"]);
    assert_eq!(human.status.code(), Some(11));
    assert!(human.stdout.is_empty());
    assert_eq!(human.stderr, output.stderr);
}

#[rstest]
#[case::unsupported_extension("notes.txt")]
#[case::no_extension("project")]
#[case::directory("folder.qgs")]
fn unsupported_or_non_file_inputs_have_exit_ten(sandbox: Sandbox, #[case] path: &str) {
    sandbox.write("notes.txt", b"<qgis/>");
    sandbox.write("project", b"<qgis/>");
    std::fs::create_dir(sandbox.path.join("folder.qgs")).unwrap();
    let output = sandbox.run(&["inspect", path, "--json"]);
    assert_eq!(output.status.code(), Some(10), "{output:?}");
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["value"], Value::Null);
    assert_eq!(report["error"]["code"], "invalid_input");
    assert_eq!(report["qgis_validation"], "not_performed");
    let message = report["error"]["message"].as_str().unwrap();
    assert!(message.contains(path));
    assert!(String::from_utf8_lossy(&output.stderr).contains(message));
    let human = sandbox.run(&["inspect", path]);
    assert_eq!(human.status.code(), Some(10));
    assert!(human.stdout.is_empty());
    assert_eq!(human.stderr, output.stderr);
}

#[cfg(unix)]
#[rstest]
fn filesystem_failure_is_not_misreported_as_missing_input(sandbox: Sandbox) {
    // A symlink loop reliably makes stat fail, including when tests run as root.
    std::os::unix::fs::symlink("loop.qgs", sandbox.path.join("loop.qgs")).unwrap();
    let output = sandbox.run(&["inspect", "loop.qgs", "--json"]);
    assert_eq!(output.status.code(), Some(14), "{output:?}");
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["value"], Value::Null);
    assert_eq!(report["error"]["code"], "filesystem_failure");
    let message = report["error"]["message"].as_str().unwrap();
    assert!(message.contains("loop.qgs"));
    assert!(String::from_utf8_lossy(&output.stderr).contains(message));
    let human = sandbox.run(&["inspect", "loop.qgs"]);
    assert_eq!(human.status.code(), Some(14));
    assert!(human.stdout.is_empty());
    assert_eq!(human.stderr, output.stderr);
}

#[rstest]
fn human_inspection_names_its_limits_instead_of_claiming_project_validity(sandbox: Sandbox) {
    sandbox.write("map.qgz", b"not a ZIP");
    let output = sandbox.run(&["inspect", "map.qgz"]);
    assert_eq!(output.status.code(), Some(0), "{output:?}");
    assert!(output.stderr.is_empty());
    assert_eq!(String::from_utf8(output.stdout).unwrap(),
        "inspection: file_metadata\npath: map.qgz\nformat: qgz (extension-derived)\nsize: 9 bytes\ncontents: not read or validated\nqgis_validation: not_performed\n");
}

#[rstest]
#[case::xml_not_parsed("malformed.qgs", b"<qgis", "qgs", 5)]
#[case::zip_not_parsed("archive.qgz", b"\xffnot a ZIP", "qgz", 10)]
#[case::empty_file("empty.qgs", b"", "qgs", 0)]
#[case::unicode_and_spaces("./żółć mapa.QGS", b"<qgis/>", "qgs", 7)]
#[case::leading_dash("-map.QGZ", b"<qgis/>", "qgz", 7)]
fn formats_come_from_the_supplied_path_not_from_contents(
    sandbox: Sandbox,
    #[case] path: &str,
    #[case] contents: &[u8],
    #[case] format: &str,
    #[case] size: u64,
) {
    sandbox.write(path, contents);
    let output = sandbox.run(&["inspect", "--json", "--", path]);
    assert_eq!(output.status.code(), Some(0), "{output:?}");
    assert!(output.stderr.is_empty());
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(
        report,
        json!({
            "inspection": "file_metadata", "qgis_validation": "not_performed",
            "value": {"path": path, "format": format, "size_bytes": size}, "error": null
        })
    );
}

#[rstest]
fn absolute_paths_are_reported_without_rewriting(sandbox: Sandbox) {
    sandbox.write("map.qgs", b"<qgis/>");
    let path = sandbox.path.join("map.qgs");
    let output = sandbox.run(&["inspect", path.to_str().unwrap(), "--json"]);
    assert_eq!(output.status.code(), Some(0), "{output:?}");
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["value"]["path"], path.to_str().unwrap());
}

#[cfg(unix)]
#[rstest]
fn symlinks_follow_regular_targets_but_keep_the_supplied_name(sandbox: Sandbox) {
    sandbox.write("target.bin", b"not a ZIP");
    std::os::unix::fs::symlink("target.bin", sandbox.path.join("alias.QGZ")).unwrap();
    let output = sandbox.run(&["inspect", "alias.QGZ", "--json"]);
    assert_eq!(output.status.code(), Some(0), "{output:?}");
    assert!(output.stderr.is_empty());
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(
        report["value"],
        json!({"path": "alias.QGZ", "format": "qgz", "size_bytes": 9})
    );
}

#[cfg(unix)]
#[rstest]
#[case::dangling("missing", 11, "missing_input")]
#[case::directory("folder", 10, "invalid_input")]
fn symlink_errors_describe_the_target(
    sandbox: Sandbox,
    #[case] target: &str,
    #[case] exit: i32,
    #[case] code: &str,
) {
    std::fs::create_dir(sandbox.path.join("folder")).unwrap();
    std::os::unix::fs::symlink(target, sandbox.path.join("alias.qgs")).unwrap();
    let output = sandbox.run(&["inspect", "alias.qgs", "--json"]);
    assert_eq!(output.status.code(), Some(exit), "{output:?}");
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["error"]["code"], code);
    assert!(report["error"]["message"]
        .as_str()
        .unwrap()
        .contains("alias.qgs"));
}

#[cfg(unix)]
#[rstest]
fn special_files_are_rejected_without_opening_them(sandbox: Sandbox) {
    let _socket = std::os::unix::net::UnixListener::bind(sandbox.path.join("socket.qgs")).unwrap();
    let output = sandbox.run(&["inspect", "socket.qgs", "--json"]);
    assert_eq!(output.status.code(), Some(10), "{output:?}");
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["error"]["code"], "invalid_input");
    assert!(report["error"]["message"]
        .as_str()
        .unwrap()
        .contains("not a regular file"));
}

#[rstest]
fn usage_errors_keep_exit_two_and_help_explains_the_inspection_scope(sandbox: Sandbox) {
    for args in [
        vec!["inspect"],
        vec!["inspect", "--json"],
        vec!["inspect", "map.qgs", "extra"],
        vec!["inspect", "map.qgs", "--unknown"],
    ] {
        let output = sandbox.run(&args);
        assert_eq!(output.status.code(), Some(2), "{output:?}");
        assert!(output.stdout.is_empty());
        assert!(!output.stderr.is_empty());
    }
    let help = sandbox.run(&["inspect", "--help"]);
    assert_eq!(help.status.code(), Some(0));
    assert!(help.stderr.is_empty());
    assert!(String::from_utf8_lossy(&help.stdout).contains("contents are not read or validated"));
}

#[rstest]
fn success_and_failure_do_not_modify_input_or_create_artifacts_and_configuration(sandbox: Sandbox) {
    sandbox.write("map.qgs", b"<qgis/>");
    for (path, exit) in [("map.qgs", 0), ("missing.qgs", 11)] {
        for json in [true, false] {
            let mut args = vec!["inspect", path];
            if json {
                args.push("--json");
            }
            assert_eq!(sandbox.run(&args).status.code(), Some(exit));
        }
    }
    assert_eq!(
        std::fs::read(sandbox.path.join("map.qgs")).unwrap(),
        b"<qgis/>"
    );
    let entries: Vec<_> = std::fs::read_dir(&sandbox.path)
        .unwrap()
        .map(|entry| entry.unwrap().file_name())
        .collect();
    assert_eq!(entries, vec![std::ffi::OsString::from("map.qgs")]);
}

#[cfg(unix)]
#[rstest]
fn paths_that_json_cannot_represent_fail_without_panicking_or_lossy_success(sandbox: Sandbox) {
    use std::ffi::{OsStr, OsString};
    use std::os::unix::ffi::OsStringExt;

    let name = OsString::from_vec(b"map-\xff.qgs".to_vec());
    std::fs::write(sandbox.path.join(&name), b"<qgis/>").unwrap();
    let output = sandbox.run(&[OsStr::new("inspect"), &name, OsStr::new("--json")]);
    assert_eq!(output.status.code(), Some(10), "{output:?}");
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["error"]["code"], "invalid_input");
    assert!(report["error"]["message"]
        .as_str()
        .unwrap()
        .contains("UTF-8"));
    assert!(report["value"].is_null());
    let human = sandbox.run(&[OsStr::new("inspect"), &name]);
    assert_eq!(human.status.code(), Some(10));
    assert!(human.stdout.is_empty());
    assert_eq!(human.stderr, output.stderr);
}
