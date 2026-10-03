use qgis_sys::native_manager_ffi as manager;
use serde_json::{json, Value};

fn test_data_path() -> String {
    format!("{}/tests/fixtures/points.gpkg", env!("CARGO_MANIFEST_DIR"))
}

fn request(operation: &str, payload: Value) -> Value {
    serde_json::from_str(&manager::invoke(
        &json!({
            "transport_version": 1,
            "operation": operation,
            "payload": payload,
        })
        .to_string(),
    ))
    .expect("manager returns JSON")
}

fn ok(operation: &str, payload: Value) -> Value {
    let response = request(operation, payload);
    assert_eq!(response["ok"], true, "manager rejected request: {response}");
    response["result"].clone()
}

fn open_test_layer() -> u64 {
    ok("app_init", Value::Null);
    let created = ok(
        "layer_new",
        json!({
            "uri": test_data_path(),
            "name": "points",
            "provider": "ogr",
        }),
    );
    assert_eq!(created["is_valid"], true);
    created["layer_id"].as_u64().expect("integer layer id")
}

#[test]
fn layer_is_valid() {
    let layer_id = open_test_layer();
    assert_eq!(
        ok("layer_is_valid", json!({"layer_id": layer_id}))["is_valid"],
        true
    );
}

#[test]
fn layer_name() {
    let layer_id = open_test_layer();
    assert_eq!(
        ok("layer_name", json!({"layer_id": layer_id}))["name"],
        "points"
    );
}

#[test]
fn layer_feature_count() {
    let layer_id = open_test_layer();
    assert_eq!(
        ok("layer_feature_count", json!({"layer_id": layer_id}))["feature_count"],
        3
    );
}

#[test]
fn layer_crs() {
    let layer_id = open_test_layer();
    assert_eq!(
        ok("layer_crs_authid", json!({"layer_id": layer_id}))["auth_id"],
        "EPSG:4326"
    );
}

#[test]
fn layer_geometry_type() {
    let layer_id = open_test_layer();
    let geom = ok("layer_geometry_type_name", json!({"layer_id": layer_id}));
    assert!(geom["name"].as_str().unwrap().contains("Point"));
}

#[test]
fn layer_fields_expose_schema_metadata() {
    let layer_id = open_test_layer();
    let fields = ok("layer_fields", json!({"layer_id": layer_id}));
    assert_eq!(fields["fields"][0]["name"], "fid");
    assert_eq!(fields["fields"][0]["type"], "Integer64");
    assert_eq!(fields["fields"][0]["precision"], 0);
    assert_eq!(fields["fields"][1]["name"], "name");
    assert_eq!(fields["fields"][1]["type"], "String");
    assert_eq!(fields["fields"][1]["precision"], 0);
}
