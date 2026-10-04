#![cfg(feature = "qgis")]

use qgis_sys::native_manager_ffi as manager;
use rstest::{fixture, rstest};
use serde_json::{json, Value};

/// The native manager seen through its one entry point.
struct Manager;

impl Manager {
    /// The `result` of a request that must succeed.
    fn result(&self, operation: &str, payload: Value) -> Value {
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
}

#[fixture]
fn native_manager() -> Manager {
    Manager
}

#[rstest]
fn shutdown_releases_layers_left_open_on_the_owner_thread(native_manager: Manager) {
    native_manager.result("app_init", Value::Null);
    native_manager.result(
        "layer_open",
        json!({
            "uri": format!("{}/tests/fixtures/points.gpkg", env!("CARGO_MANIFEST_DIR")),
            "provider": "ogr",
            "name": "points",
        }),
    );

    let shutdown = native_manager.result("app_shutdown", Value::Null);
    assert_eq!(shutdown["shutdown"], true);
    assert_eq!(shutdown["released_layer_count"], 1);
}
