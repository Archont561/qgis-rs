//! N-API adapter for the `qgis-rs` npm package.
//!
//! One function, taking and returning JSON text — the same surface the PyO3
//! adapter exposes, for the same reason. Every operation qgis-rs has is an
//! `Operation` in `qgis-protocol`; a binding that mirrored the engine's
//! function list would need a new export here, a new signature in
//! `index.d.ts`, and a rebuilt addon for every operation the engine grows.
//!
//! The ergonomic API — `Extent`, `Project`, `TilePlan` and friends — lives in
//! `ts-packages/qgis-node/index.js`, written in JavaScript against this
//! function. It is a *client*, not a reimplementation: the pure-JS fallback
//! that used to re-derive tile arithmetic is gone, because there is no longer
//! anything to re-derive.
//!
//! See `.knowledge/decisions/D09-wire-protocol-over-ffi.md`.

use napi_derive::napi;

/// Run one transport request and return one transport response, both as JSON
/// text.
#[napi]
#[must_use]
// `&str` is the signature this function wants — the engine takes a slice and
// nothing here owns the text — but napi-rs rejects it: a JavaScript string is
// primitive and cannot be lent to Rust. `String` is the only signature that
// compiles, so the lint is silenced on this item rather than workspace-wide,
// where it would also hide a real ownership mistake elsewhere.
#[allow(clippy::needless_pass_by_value)]
pub fn invoke(request: String) -> String {
    qgis_engine::invoke(&request)
}

/// The transport version this addon was built against.
///
/// `u32` rather than `i32` because the envelope's field is unsigned; napi maps
/// it to a JavaScript number either way.
#[napi]
#[must_use]
pub const fn transport_version() -> u32 {
    qgis_engine::TRANSPORT_VERSION
}
