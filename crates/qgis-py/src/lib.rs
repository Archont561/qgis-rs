//! `PyO3` adapter for the `qgis-rs` Python distribution.
//!
//! One function, taking and returning JSON text. That is the whole extension
//! module on purpose: every operation qgis-rs has is an `Operation` in
//! `qgis-protocol`, so adding one is a change to that enum and to
//! `qgis-engine` — not a new `#[pyfunction]` here, a new entry in
//! `qgis_rs/__init__.pyi`, a matching `#[napi]` export in the Node addon, and a
//! release of both wheels to go with it.
//!
//! The ergonomic API — `Extent`, `Project`, `TilePlan` and friends — lives in
//! `py-packages/qgis-rs/python/qgis_rs/`, written in Python against this
//! function. It is a *client*, not a reimplementation: every rule it needs
//! (parsing, validation, tile arithmetic) is asked of the engine.
//!
//! See `.knowledge/decisions/D09-wire-protocol-over-ffi.md`.
//!
//! The wheel also ships the `qgis-cli` binary built from `src/bin/qgis-cli.rs`;
//! that is a separate target and does not go through this boundary.

use pyo3::prelude::*;

/// Run one transport request and return one transport response, both as JSON
/// text.
///
/// Public so the crate's own tests can drive the adapter without an interpreter
/// attached. The GIL is released for the duration of the call: the engine is
/// pure Rust and touches no Python object, so a long `plan_tiles` must not stop
/// other Python threads.
#[pyfunction]
#[must_use]
pub fn invoke(python: Python<'_>, request: &str) -> String {
    python.allow_threads(|| qgis_engine::invoke(request))
}

/// The transport version this extension was built against.
///
/// Exposed so the Python client can refuse an engine it cannot speak to,
/// instead of discovering the mismatch one field at a time.
#[pyfunction]
#[must_use]
pub const fn transport_version() -> u32 {
    qgis_engine::TRANSPORT_VERSION
}

/// The extension module the `qgis_rs` package imports as `qgis_rs._core`.
#[pymodule]
fn _core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(invoke, module)?)?;
    module.add_function(wrap_pyfunction!(transport_version, module)?)?;
    module.add("TRANSPORT_VERSION", qgis_engine::TRANSPORT_VERSION)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn the_adapter_forwards_to_the_engine_verbatim() {
        // No interpreter here: what is under test is that this crate adds
        // nothing to the request on its way across the boundary.
        let request = r#"{"transport_version":1,"operation":"ping","payload":"hello"}"#;
        assert_eq!(qgis_engine::invoke(request), qgis_engine::invoke(request));
        assert!(qgis_engine::invoke(request).contains("\"echo\":\"hello\""));
    }
}
