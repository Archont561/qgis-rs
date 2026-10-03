//! The Rust side of the native QGIS manager boundary.
//!
//! RFC 19 deliberately exposes one JSON C ABI instead of a collection of
//! per-class CXX shims. QGIS objects remain owned by the manager's dedicated
//! thread and callers receive copied protocol values or structured errors.

pub mod native_manager;

pub use native_manager as native_manager_ffi;
