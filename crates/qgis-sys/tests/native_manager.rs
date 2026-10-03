use qgis_sys::native_manager_ffi as manager;
use serde_json::{json, Value};

fn response(request: Value) -> Value {
    serde_json::from_str(&manager::invoke(&request.to_string())).expect("manager returns JSON")
}

fn ok(operation: &str, payload: Value) -> Value {
    let answer = response(json!({
        "transport_version": 1,
        "operation": operation,
        "payload": payload,
    }));
    assert_eq!(answer["ok"], true, "manager rejected request: {answer}");
    assert_eq!(answer["transport_version"], 1);
    answer["result"].clone()
}

#[test]
fn manager_initializes_and_reports_engine_info() {
    let initialized = ok("app_init", Value::Null);
    assert_eq!(initialized["initialized"], true);

    let info = ok("engine_info", Value::Null);
    assert_eq!(info["transport_version"], 1);
    assert!(info["qgis_version"].as_str().unwrap().contains('.'));
    assert!(info["operations"]
        .as_array()
        .unwrap()
        .iter()
        .any(|operation| operation == "layer_new"));
}

#[test]
fn manager_routes_vector_layer_operations_through_owned_ids() {
    ok("app_init", Value::Null);
    let path = format!("{}/tests/fixtures/points.gpkg", env!("CARGO_MANIFEST_DIR"));
    let created = ok(
        "layer_new",
        json!({"uri": path, "name": "points", "provider": "ogr"}),
    );
    let layer_id = created["layer_id"].as_u64().expect("integer layer id");
    assert_eq!(created["is_valid"], true);

    assert_eq!(
        ok("layer_is_valid", json!({"layer_id": layer_id}))["is_valid"],
        true
    );
    assert_eq!(
        ok("layer_name", json!({"layer_id": layer_id}))["name"],
        "points"
    );
    assert_eq!(
        ok("layer_feature_count", json!({"layer_id": layer_id}))["feature_count"],
        3
    );
    assert_eq!(
        ok("layer_crs_authid", json!({"layer_id": layer_id}))["auth_id"],
        "EPSG:4326"
    );
    assert!(
        ok("layer_geometry_type_name", json!({"layer_id": layer_id}))["name"]
            .as_str()
            .unwrap()
            .contains("Point")
    );

    let fields = ok("layer_fields", json!({"layer_id": layer_id}));
    assert_eq!(fields["fields"][0]["name"], "fid");
    assert_eq!(fields["fields"][0]["type"], "Integer64");
    assert_eq!(fields["fields"][1]["name"], "name");
    assert_eq!(fields["fields"][1]["type"], "String");
}

#[test]
fn manager_rejects_invalid_requests_and_ids_as_error_envelopes() {
    let malformed: Value = serde_json::from_str(&manager::invoke("not json")).unwrap();
    assert_eq!(malformed["ok"], false);
    assert_eq!(malformed["result"]["kind"], "invalid_request");

    ok("app_init", Value::Null);
    let invalid_id = response(json!({
        "transport_version": 1,
        "operation": "layer_name",
        "payload": {"layer_id": 999_999}
    }));
    assert_eq!(invalid_id["ok"], false);
    assert_eq!(invalid_id["result"]["kind"], "invalid_object_id");
}

#[test]
fn concurrent_callers_are_serialized_by_the_manager_owner() {
    ok("app_init", Value::Null);
    let workers = (0..4)
        .map(|_| {
            std::thread::spawn(|| {
                let info = ok("engine_info", Value::Null);
                assert_eq!(info["initialized"], true);
            })
        })
        .collect::<Vec<_>>();

    for worker in workers {
        worker.join().expect("manager caller should not panic");
    }
}

#[test]
fn transport_version_is_available_without_starting_qgis() {
    assert_eq!(manager::transport_version(), 1);
}
