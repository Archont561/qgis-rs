use qgis_sys::native_manager_ffi as manager;
use serde_json::{json, Value};

fn result(operation: &str, payload: Value) -> Value {
    let response: Value = serde_json::from_str(&manager::invoke(
        &json!({
            "transport_version": 1,
            "operation": operation,
            "payload": payload,
        })
        .to_string(),
    ))
    .expect("manager returns JSON");
    assert_eq!(response["ok"], true, "manager rejected request: {response}");
    response["result"].clone()
}

#[test]
fn shutdown_releases_layers_left_open_on_the_owner_thread() {
    result("app_init", Value::Null);
    result(
        "layer_open",
        json!({
            "uri": format!("{}/tests/fixtures/points.gpkg", env!("CARGO_MANIFEST_DIR")),
            "provider": "ogr",
            "name": "points",
        }),
    );

    let shutdown = result("app_shutdown", Value::Null);
    assert_eq!(shutdown["shutdown"], true);
    assert_eq!(shutdown["released_layer_count"], 1);
}
