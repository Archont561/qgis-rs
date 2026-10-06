//! The API-manifest generator's public seam: JSON in, validated/generated text out.

use xtask::api_manifest::{
    check_summary, render_generated_header, render_operation_table, validate_manifest,
};

const MANIFEST: &str =
    include_str!("../../../crates/qgis-sys/native_manager/generated/api_manifest.json");
const GENERATED_TABLE: &str =
    include_str!("../../../crates/qgis-sys/include/native_manager/generated/operation_table.inc");

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
fn a_successful_check_summarizes_the_manifest_and_generated_fragments() {
    let manifest = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    assert_eq!(
        check_summary(&manifest, 2),
        "api-manifest: 17 operations match 2 generated fragments"
    );
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
        "source": {"extractor": "test"},
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

// --- The manifest as the single authority for wire spellings -----------------
//
// `Operation::all()` is a hand-written list of wire names, and the manifest
// generates another. Nothing used to compare them, so a native operation could
// be added, renamed or dropped on one side while the other stayed silent —
// which is the second hand-written operation spelling table TASK-30 AC#2
// forbids. These tests damage each side in turn and require the gate to say so.

#[test]
fn the_manifest_accounts_for_every_operation_the_transport_serves() {
    let manifest = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    let served = qgis_protocol::Operation::all();
    xtask::api_manifest::check_wire_operations(&manifest, served)
        .expect("the manifest partitions the served operations");
    assert_eq!(
        xtask::api_manifest::wire_check_summary(&manifest, served.len()),
        "check-api-operations: 17 generated plus 12 excluded operations account for all 29 \
         wire spellings"
    );
}

#[test]
fn a_generated_operation_the_transport_does_not_serve_is_named() {
    let mut manifest = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    manifest.operations[6].name = "layer_opened".to_string();
    let error =
        xtask::api_manifest::check_wire_operations(&manifest, qgis_protocol::Operation::all())
            .expect_err("a renamed operation must fail the gate");
    let message = error.to_string();
    assert!(message.contains("layer_opened"), "{message}");
    assert!(message.contains("layer_open"), "{message}");
}

#[test]
fn an_operation_dropped_from_the_manifest_is_not_silently_absorbed() {
    let mut manifest = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    let dropped = manifest.operations.pop().expect("manifest has operations");
    let error =
        xtask::api_manifest::check_wire_operations(&manifest, qgis_protocol::Operation::all())
            .expect_err("a dropped operation must fail the gate");
    assert!(error.to_string().contains(&dropped.name));
}

#[test]
fn an_operation_added_to_the_transport_alone_is_named() {
    let manifest = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    let mut served: Vec<&str> = qgis_protocol::Operation::all().to_vec();
    served.push("layer_rename");
    let error = xtask::api_manifest::check_wire_operations(&manifest, &served)
        .expect_err("an unreviewed transport operation must fail the gate");
    assert!(error.to_string().contains("layer_rename"));
}

#[test]
fn an_exclusion_for_an_operation_nobody_serves_is_named() {
    let mut manifest = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    manifest.exclusions[0]
        .operations
        .push("tile_retire".to_string());
    let error =
        xtask::api_manifest::check_wire_operations(&manifest, qgis_protocol::Operation::all())
            .expect_err("a stale exclusion must fail the gate");
    assert!(error.to_string().contains("tile_retire"));
}

#[test]
fn an_operation_cannot_be_generated_and_excluded_at_once() {
    let both = MANIFEST.replace(
        r#""reason": "Qt widgets and QgisInterface require a host-owned GUI thread.""#,
        r#""reason": "Qt widgets and QgisInterface require a host-owned GUI thread.",
      "operations": ["layer_open"]"#,
    );
    let error = validate_manifest(&both).expect_err("an excluded generated operation must fail");
    assert!(error.to_string().contains("layer_open"));
}

#[test]
fn a_supported_exclusion_cannot_carry_operations() {
    let supported = MANIFEST.replace(
        r#""scope": "engine-transport",
      "status": "unsupported","#,
        r#""scope": "engine-transport",
      "status": "supported","#,
    );
    let error = validate_manifest(&supported).expect_err("a supported exclusion must fail");
    assert!(error.to_string().contains("engine-transport"));
}
