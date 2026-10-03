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
fn manifest_upgrade_diff_rejects_drops_and_ownership_changes() {
    let current = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");

    let mut dropped = current.clone();
    dropped.declarations.pop();
    let error = xtask::api_manifest::check_upgrade(&current, &dropped)
        .expect_err("dropped declaration must fail review");
    assert!(error.to_string().contains("dropped"));

    let mut reowned = current.clone();
    reowned.declarations[0].ownership = Some("qgis_owned".to_string());
    let error = xtask::api_manifest::check_upgrade(&current, &reowned)
        .expect_err("ownership change must fail review");
    assert!(error.to_string().contains("ownership"));
}

#[test]
fn operation_handlers_must_match_the_supported_declaration() {
    let mismatch = MANIFEST.replace(
        "\"name\": \"api_describe\",\n      \"handler\": \"api_describe\",",
        "\"name\": \"api_describe\",\n      \"handler\": \"engine_info\",",
    );
    let error = validate_manifest(&mismatch).expect_err("handler mismatch must fail");
    assert!(error.to_string().contains("handler"));
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
        "mappings": [
            {"category":"ownership","qgis_type":"x","wire_type":"x","rule":"x"},
            {"category":"invalidation","qgis_type":"x","wire_type":"x","rule":"x"},
            {"category":"overload","qgis_type":"x","wire_type":"x","rule":"x"},
            {"category":"enum","qgis_type":"x","wire_type":"x","rule":"x"},
            {"category":"variant","qgis_type":"x","wire_type":"x","rule":"x"},
            {"category":"binary_artifact","qgis_type":"x","wire_type":"x","rule":"x"},
            {"category":"paging","qgis_type":"x","wire_type":"x","rule":"x"}
        ],
        "operations": [
            {"name": "one", "handler": "one", "codec": "json_object", "requires_initialization": true},
            {"name": "one", "handler": "two", "codec": "json_object", "requires_initialization": true}
        ]
    }"#;
    let error = validate_manifest(invalid).expect_err("invalid manifest must fail");
    let message = error.to_string();
    assert!(message.contains("status") || message.contains("duplicate operation"));
}
