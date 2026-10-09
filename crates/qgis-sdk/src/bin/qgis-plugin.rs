//! `qgis-plugin` — the canonical plugin-development CLI (D13 §1).
//!
//! The command tree and handlers live in `qgis-sdk-core`; this binary only
//! passes its process arguments to that library.

fn main() -> std::process::ExitCode {
    qgis_sdk_core::main_entry()
}
