use qgis_sys::native_manager_ffi as manager;
use serde_json::{json, Value};

#[test]
fn lifecycle_and_info() {
    let response: Value = serde_json::from_str(&manager::invoke(
        &json!({
            "transport_version": 1,
            "operation": "app_init",
            "payload": null,
        })
        .to_string(),
    ))
    .expect("manager returns JSON");
    assert_eq!(response["ok"], true);
    assert_eq!(response["result"]["initialized"], true);

    let info: Value = serde_json::from_str(&manager::invoke(
        &json!({
            "transport_version": 1,
            "operation": "engine_info",
            "payload": null,
        })
        .to_string(),
    ))
    .expect("manager returns JSON");
    assert_eq!(info["ok"], true);
    assert!(info["result"]["qgis_version"]
        .as_str()
        .expect("QGIS version")
        .contains('.'));
    assert!(!info["result"]["qt_version"].as_str().unwrap().is_empty());
    assert!(!info["result"]["platform"].as_str().unwrap().is_empty());
}
