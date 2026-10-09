//! `qgis-sdk` — the exact alias of `qgis-sdk` (D13 §1).
//!
//! It runs the same `qgis-sdk-core` parser and handlers as `qgis-sdk`, so
//! `qgis-sdk --help` and every exit code are identical to `qgis-sdk`'s.

fn main() -> std::process::ExitCode {
    qgis_sdk_core::main_entry()
}
