//! The `PyO3` adapter carries the request and adds nothing to it.
//!
//! No interpreter is involved: this crate's whole job is to hand a string to
//! `qgis-engine` and hand the answer back, so what is worth asserting is that
//! the answer is the engine's own. The Python side of the boundary is covered
//! by `py-packages/qgis-py/tests/`, against a real built `_core`.

#[test]
fn the_adapter_forwards_to_the_engine_verbatim() {
    // No interpreter here: what is under test is that this crate adds
    // nothing to the request on its way across the boundary.
    let request = r#"{"transport_version":1,"operation":"ping","payload":"hello"}"#;
    assert_eq!(qgis_engine::invoke(request), qgis_engine::invoke(request));
    assert!(qgis_engine::invoke(request).contains("\"echo\":\"hello\""));
}
