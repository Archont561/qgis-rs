//! Public seam for the language-neutral bridge fixture validator.

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use serde_json::{json, Value};
use xtask::bridge_fixtures::validate_tree;

static NEXT_TEMP: AtomicU64 = AtomicU64::new(0);

fn fixture_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../test-fixtures/bridge")
}

fn copy_fixture_tree() -> PathBuf {
    let root = std::env::temp_dir().join(format!(
        "qgis-rs-bridge-fixtures-{}-{}",
        std::process::id(),
        NEXT_TEMP.fetch_add(1, Ordering::Relaxed)
    ));
    fs::create_dir_all(&root).expect("create temporary fixture root");
    copy_dir(&fixture_root(), &root);
    root
}

fn copy_dir(source: &Path, destination: &Path) {
    for entry in fs::read_dir(source).expect("read fixture directory") {
        let entry = entry.expect("fixture entry");
        let destination = destination.join(entry.file_name());
        if entry.file_type().expect("fixture type").is_dir() {
            fs::create_dir_all(&destination).expect("create fixture directory");
            copy_dir(&entry.path(), &destination);
        } else {
            fs::copy(entry.path(), destination).expect("copy fixture");
        }
    }
}

fn mutate(root: &Path, relative: &str, change: impl FnOnce(&mut Value)) {
    let path = root.join(relative);
    let mut value: Value =
        serde_json::from_str(&fs::read_to_string(&path).expect("read JSON")).expect("parse JSON");
    change(&mut value);
    fs::write(
        path,
        serde_json::to_string_pretty(&value).expect("render JSON"),
    )
    .expect("write JSON");
}

#[test]
fn checked_in_cross_language_fixtures_validate() {
    let summary = validate_tree(&fixture_root()).expect("fixture tree is valid");
    assert_eq!(
        summary,
        "bridge-fixtures: 4 descriptions, 6 requests, 10 responses, 12 malformed cases, 3 events"
    );
}

#[test]
fn unknown_fields_are_rejected() {
    let root = copy_fixture_tree();
    mutate(&root, "requests/qgis-layers-list.json", |request| {
        request["surprise"] = json!(true);
    });
    let error = validate_tree(&root).expect_err("unknown field must fail");
    assert!(
        format!("{error:#}").contains("unknown field `surprise`"),
        "{error:#}"
    );
    fs::remove_dir_all(root).expect("remove temporary fixture tree");
}

#[test]
fn request_ids_are_required() {
    let root = copy_fixture_tree();
    mutate(&root, "requests/qgis-layers-list.json", |request| {
        request
            .as_object_mut()
            .expect("request object")
            .remove("request_id");
    });
    let error = validate_tree(&root).expect_err("missing request id must fail");
    assert!(format!("{error:#}").contains("request_id"), "{error:#}");
    fs::remove_dir_all(root).expect("remove temporary fixture tree");
}

#[test]
fn wire_names_must_be_snake_case() {
    let root = copy_fixture_tree();
    mutate(&root, "requests/qgis-layers-list.json", |request| {
        request["method"] = json!("layers.addVector");
    });
    let error = validate_tree(&root).expect_err("camelCase wire name must fail");
    assert!(error.to_string().contains("snake_case"), "{error:#}");
    fs::remove_dir_all(root).expect("remove temporary fixture tree");
}

#[test]
fn incompatible_schema_versions_are_rejected() {
    let root = copy_fixture_tree();
    mutate(&root, "descriptions/qgis.json", |description| {
        description["bridge_version"] = json!(2);
    });
    let error = validate_tree(&root).expect_err("future schema must fail");
    assert!(error.to_string().contains("bridge_version"), "{error:#}");
    fs::remove_dir_all(root).expect("remove temporary fixture tree");
}
