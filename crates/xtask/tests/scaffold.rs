//! The native-manager scaffolder extends the reviewed API manifest; it never
//! recreates the CXX bridge tree that D12 replaced.

use std::fs;

use xtask::api_manifest::validate_manifest;
use xtask::scaffold::operation;

const MANIFEST: &str =
    include_str!("../../../crates/qgis-sys/native_manager/generated/api_manifest.json");

#[test]
fn scaffolding_adds_one_reviewable_native_manager_operation() {
    let directory = std::env::temp_dir().join(format!(
        "qgis-xtask-scaffold-operation-{}",
        std::process::id()
    ));
    fs::create_dir_all(&directory).expect("create dir");
    let path = directory.join("api_manifest.json");
    fs::write(&path, MANIFEST).expect("seed manifest");

    operation(&path, "project_save", "project_save").expect("scaffold operation");

    let updated = fs::read_to_string(&path).expect("read manifest");
    let manifest = validate_manifest(&updated).expect("scaffold remains valid");
    assert!(manifest.operations.iter().any(|entry| {
        entry.name == "project_save"
            && entry.handler == "project_save"
            && entry.codec == "json_object"
            && entry.request_codec == "json_object"
            && entry.result_codec == "json_object"
            && entry.requires_initialization
    }));
    assert!(manifest.declarations.iter().any(|entry| {
        entry.id == "NativeManager::project_save"
            && entry.operation.as_deref() == Some("project_save")
            && entry.handler.as_deref() == Some("project_save")
    }));
}

#[test]
fn scaffolding_refuses_to_duplicate_an_operation() {
    let directory = std::env::temp_dir().join(format!(
        "qgis-xtask-scaffold-duplicate-{}",
        std::process::id()
    ));
    fs::create_dir_all(&directory).expect("create dir");
    let path = directory.join("api_manifest.json");
    fs::write(&path, MANIFEST).expect("seed manifest");

    let error = operation(&path, "engine_info", "engine_info")
        .expect_err("existing operation must not be overwritten");
    assert!(error.to_string().contains("already exists"));
}
