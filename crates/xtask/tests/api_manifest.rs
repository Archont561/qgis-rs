//! The API-manifest generator's public seam: JSON in, validated/generated text out.

use xtask::api_manifest::{render_generated_header, render_operation_table, validate_manifest};

const MANIFEST: &str = include_str!("../../../crates/qgis-sys/native_manager/generated/api_manifest.json");
const GENERATED_TABLE: &str = include_str!(
    "../../../crates/qgis-sys/include/native_manager/generated/operation_table.inc"
);

#[test]
fn the_checked_in_manifest_has_a_complete_operation_registry() {
    let manifest = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    assert_eq!(manifest.manifest_version, 1);
    assert_eq!(manifest.qgis.min_version, "3.44.9");
    assert!(manifest.declarations.len() >= manifest.operations.len());
    for category in [
        "ownership",
        "invalidation",
        "overload",
        "enum",
        "variant",
        "binary_artifact",
        "paging",
    ] {
        assert!(manifest
            .mappings
            .iter()
            .any(|mapping| mapping.category == category));
    }
    assert!(manifest
        .declarations
        .iter()
        .all(|declaration| !declaration.reason.is_empty()));

    let generated = render_operation_table(&manifest).expect("operation table renders");
    assert_eq!(generated, GENERATED_TABLE);
}

#[test]
fn generated_header_exposes_the_pinned_api_version() {
    let manifest = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    let header = render_generated_header(&manifest);
    assert!(header.contains("QGIS_API_MANIFEST_VERSION 1"));
    assert!(header.contains("QGIS_API_MANIFEST_QGIS_MIN_VERSION \"3.44.9\""));
    assert!(header.contains("QGIS_API_MANIFEST_QGIS_TESTED_VERSION \"3.44.14\""));
}

#[test]
fn invalid_statuses_and_duplicate_operations_are_rejected() {
    let invalid = r#"{
        "manifest_version": 1,
        "qgis": {"min_version": "3.44.9", "tested_version": "3.44.14"},
        "declarations": [{
            "id": "QgsThing::value",
            "kind": "method",
            "module": "core",
            "status": "invented",
            "since": "3.0",
            "version_range": ">=3.0,<4",
            "reason": "test"
        }],
        "operations": [
            {"name": "one", "handler": "one", "requires_initialization": true},
            {"name": "one", "handler": "two", "requires_initialization": true}
        ]
    }"#;
    let error = validate_manifest(invalid).expect_err("invalid manifest must fail");
    let message = error.to_string();
    assert!(message.contains("status") || message.contains("duplicate operation"));
}
