//! The API-manifest generator's public seam: JSON in, validated/generated text out.

use std::{
    fs,
    path::{Path, PathBuf},
};

use xtask::api_manifest::{
    baseline_summary, check_baseline, check_summary, render_generated_header,
    render_operation_table, validate_manifest, verify_repository, BASELINE_PATH, GENERATED_DIR,
    MANIFEST_PATH,
};

const MANIFEST: &str =
    include_str!("../../../crates/qgis-sys/native_manager/generated/api_manifest.json");
const BASELINE: &str =
    include_str!("../../../crates/qgis-sys/native_manager/generated/api_manifest.baseline.json");
const GENERATED_TABLE: &str =
    include_str!("../../../crates/qgis-sys/include/native_manager/generated/operation_table.inc");
const GENERATED_HEADER: &str =
    include_str!("../../../crates/qgis-sys/include/native_manager/generated/api_manifest.h");

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
    assert!(manifest.operations.iter().all(|operation| {
        operation.request_codec != "json_object" && operation.result_codec != "json_object"
    }));
    let layer_open = manifest
        .operations
        .iter()
        .find(|operation| operation.name == "layer_open")
        .expect("layer_open codec metadata");
    assert_eq!(layer_open.request_codec, "layer_open_request");
    assert_eq!(layer_open.result_codec, "layer_open_result");

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
fn codec_names_must_be_cpp_identifiers() {
    let invalid_request = MANIFEST.replace(
        "\"request_codec\": \"layer_open_request\"",
        "\"request_codec\": \"layer-open-request\"",
    );
    assert_ne!(
        invalid_request, MANIFEST,
        "fixture contains request codec metadata"
    );
    let error =
        validate_manifest(&invalid_request).expect_err("invalid request codec name must fail");
    assert!(error.to_string().contains("request codec"));

    let invalid_result = MANIFEST.replace(
        "\"result_codec\": \"layer_open_result\"",
        "\"result_codec\": \"layer-open-result\"",
    );
    assert_ne!(
        invalid_result, MANIFEST,
        "fixture contains result codec metadata"
    );
    let error =
        validate_manifest(&invalid_result).expect_err("invalid result codec name must fail");
    assert!(error.to_string().contains("result codec"));
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

// --- The pinned baseline and the gate's API diff ----------------------------
//
// AC#5 asks for a QGIS upgrade to produce an API diff that fails review when a
// declaration is silently dropped or ownership metadata changes. `check_upgrade`
// could already answer that question, but nothing in the gate ever asked it: the
// lint called `run(true, None)`, so the diff path had no trigger. These tests
// pin the baseline file into the gate and damage it, because a check nobody has
// seen fail is a check nobody has tested.

/// A scratch repository root holding the four files `verify_repository` reads.
fn scratch_repository(name: &str) -> PathBuf {
    let root =
        std::env::temp_dir().join(format!("xtask-api-manifest-{name}-{}", std::process::id()));
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(root.join(GENERATED_DIR)).expect("create scratch generated directory");
    fs::create_dir_all(
        root.join(MANIFEST_PATH)
            .parent()
            .expect("manifest path has a parent"),
    )
    .expect("create scratch manifest directory");
    write_scratch(&root, MANIFEST, BASELINE, GENERATED_TABLE, GENERATED_HEADER);
    root
}

fn write_scratch(root: &Path, manifest: &str, baseline: &str, table: &str, header: &str) {
    fs::write(root.join(MANIFEST_PATH), manifest).expect("write scratch manifest");
    fs::write(root.join(BASELINE_PATH), baseline).expect("write scratch baseline");
    fs::write(root.join(GENERATED_DIR).join("operation_table.inc"), table)
        .expect("write scratch operation table");
    fs::write(root.join(GENERATED_DIR).join("api_manifest.h"), header)
        .expect("write scratch generated header");
}

fn serialize(manifest: &xtask::api_manifest::ApiManifest) -> String {
    let mut text = serde_json::to_string_pretty(manifest).expect("serialize manifest");
    text.push('\n');
    text
}

#[test]
fn the_checked_in_manifest_matches_its_pinned_baseline() {
    let pinned = validate_manifest(BASELINE).expect("checked-in baseline is valid");
    let current = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");

    check_baseline(&pinned, &current).expect("the manifest is exactly the reviewed snapshot");
    // Structural equality, not a subset check: the pin is a snapshot of the
    // whole reviewed surface, so prose and version fields drift too.
    assert_eq!(pinned, current);

    assert_eq!(
        baseline_summary(&current),
        "api-manifest baseline: crates/qgis-sys/native_manager/generated/api_manifest.baseline.json \
         matches at QGIS 3.44.14 with 17 declarations and 17 operations"
    );
}

#[test]
fn baseline_drift_names_a_dropped_declaration_and_operation() {
    let pinned = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    let mut current = pinned.clone();
    let dropped_declaration = current
        .declarations
        .pop()
        .expect("manifest has declarations");
    let dropped_operation = current.operations.pop().expect("manifest has operations");

    let error = check_baseline(&pinned, &current).expect_err("a silent drop must fail review");
    let message = error.to_string();
    assert!(message.contains("declaration dropped"), "{message}");
    assert!(message.contains(&dropped_declaration.id), "{message}");
    assert!(message.contains("operation dropped"), "{message}");
    assert!(message.contains(&dropped_operation.name), "{message}");
}

#[test]
fn baseline_drift_names_an_added_declaration_and_operation() {
    let pinned = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    let mut current = pinned.clone();
    let mut added = current.declarations[0].clone();
    added.id = "QgsVectorLayer::setName".to_string();
    current.declarations.push(added);
    current
        .operations
        .push(xtask::api_manifest::OperationDefinition {
            name: "layer_rename".to_string(),
            handler: "layer_rename".to_string(),
            codec: "json_object".to_string(),
            request_codec: "layer_rename_request".to_string(),
            result_codec: "layer_rename_result".to_string(),
            requires_initialization: true,
        });

    let error = check_baseline(&pinned, &current).expect_err("an unreviewed addition must fail");
    let message = error.to_string();
    assert!(message.contains("declaration added"), "{message}");
    assert!(message.contains("QgsVectorLayer::setName"), "{message}");
    assert!(message.contains("operation added"), "{message}");
    assert!(message.contains("layer_rename"), "{message}");
}

#[test]
fn baseline_drift_names_an_ownership_change() {
    let pinned = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    let mut current = pinned.clone();
    current.declarations[0].ownership = Some("qgis_owned".to_string());

    let error = check_baseline(&pinned, &current).expect_err("an ownership change must fail");
    let message = error.to_string();
    assert!(message.contains("ownership changed"), "{message}");
    assert!(message.contains(&pinned.declarations[0].id), "{message}");
}

#[test]
fn baseline_drift_reports_every_change_in_one_run() {
    let pinned = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    let mut current = pinned.clone();
    current.declarations.pop();
    current.declarations[0].status = "partial".to_string();
    current.operations[0].request_codec = "reviewed_request".to_string();
    current.operations[0].result_codec = "reviewed_result".to_string();
    let mut added = current.declarations[0].clone();
    added.id = "QgsVectorLayer::setName".to_string();
    current.declarations.push(added);

    let error = check_baseline(&pinned, &current).expect_err("drift must fail review");
    let message = error.to_string();
    for expected in [
        "declaration dropped",
        "status changed",
        "request_codec: empty_payload -> reviewed_request",
        "result_codec: application_state_result -> reviewed_result",
        "declaration added",
        "cp crates/qgis-sys/native_manager/generated/api_manifest.json",
    ] {
        assert!(
            message.contains(expected),
            "missing {expected:?} in {message}"
        );
    }
}

#[test]
fn the_gate_verifies_a_scratch_tree_and_fails_on_damage() {
    let root = scratch_repository("gate");

    verify_repository(&root).expect("a faithful copy of the generated tree passes the gate");

    // A QGIS upgrade that silently drops an operation and the declaration that
    // supported it. Both sides have to go for the manifest to stay internally
    // valid (`validate_manifest` rejects an operation with no supported
    // declaration), which is exactly the shape a regeneration would produce —
    // and the pin still remembers them, so the gate names both.
    let mut damaged = validate_manifest(MANIFEST).expect("checked-in API manifest is valid");
    let dropped = damaged
        .declarations
        .pop()
        .expect("manifest has declarations");
    let dropped_operation = dropped
        .operation
        .clone()
        .expect("the last declaration supports an operation");
    damaged
        .operations
        .retain(|operation| operation.name != dropped_operation);
    write_scratch(
        &root,
        &serialize(&damaged),
        BASELINE,
        GENERATED_TABLE,
        GENERATED_HEADER,
    );
    let error = verify_repository(&root).expect_err("a dropped declaration must fail the gate");
    let message = error.to_string();
    assert!(message.contains(&dropped.id), "{message}");
    assert!(message.contains(&dropped_operation), "{message}");

    // The other direction: the pin itself gains a declaration nobody reviewed
    // out of the manifest, so the snapshot is not a subset of the current file.
    let mut pinned = validate_manifest(BASELINE).expect("checked-in baseline is valid");
    let mut extra = pinned.declarations[0].clone();
    extra.id = "QgsVectorLayer::setName".to_string();
    pinned.declarations.push(extra);
    write_scratch(
        &root,
        MANIFEST,
        &serialize(&pinned),
        GENERATED_TABLE,
        GENERATED_HEADER,
    );
    let error = verify_repository(&root).expect_err("a stale pin must fail the gate");
    assert!(
        error.to_string().contains("QgsVectorLayer::setName"),
        "{error}"
    );

    // And the fragments stay part of the same verification: restore a tree
    // whose manifest matches its pin, damage only the generated table, and the
    // gate still fails.
    write_scratch(&root, MANIFEST, BASELINE, GENERATED_TABLE, GENERATED_HEADER);
    fs::write(
        root.join(GENERATED_DIR).join("operation_table.inc"),
        "junk\n",
    )
    .expect("damage the scratch operation table");
    let error = verify_repository(&root).expect_err("a stale fragment must fail the gate");
    assert!(error.to_string().contains("stale"), "{error}");

    let _ = fs::remove_dir_all(&root);
}
