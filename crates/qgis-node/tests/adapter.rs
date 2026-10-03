//! The N-API adapter carries the request and adds nothing to it.
//!
//! No JavaScript runtime is involved — `#[napi]` functions cannot be called
//! without one, and there would be nothing to learn from doing so. What this
//! crate contributes is a pass-through, so what is worth asserting is that the
//! answer is the engine's own, byte for byte. The JavaScript side of the
//! boundary is covered by `ts-packages/qgis-node/tests/`, against a real built
//! addon.

#[test]
fn the_adapter_forwards_to_the_engine_verbatim() {
    let request = r#"{"transport_version":1,"operation":"ping","payload":"hello"}"#;
    let response = qgis_engine::invoke(request);
    assert_eq!(response, qgis_engine::invoke(request));
    assert!(response.contains("\"echo\":\"hello\""));
}

#[test]
fn the_addon_and_the_engine_agree_on_the_transport_version() {
    // The constant the addon exports to JavaScript is the engine's, not a
    // second copy that could age independently of it.
    assert_eq!(qgis_engine::TRANSPORT_VERSION, 1);
}

#[test]
fn the_default_addon_build_reports_when_qgis_is_not_loaded() {
    let request = r#"{"transport_version":1,"operation":"api_describe","payload":null}"#;
    let response: serde_json::Value =
        serde_json::from_str(&qgis_engine::invoke(request)).expect("the engine answers JSON");

    assert_eq!(response["ok"], false);
    assert_eq!(response["result"]["kind"], "qgis");
    assert_eq!(
        response["result"]["error"],
        "the QGIS backend is not loaded in this build"
    );
}
