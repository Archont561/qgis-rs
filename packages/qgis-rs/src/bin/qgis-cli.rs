//! `qgis-cli` binary — Rust-native CLI shipped in the `qgis-rs` Python wheel.
//!
//! When installed via `pip install qgis-rs`, maturin places this binary on
//! PATH as `qgis-cli`. The Python wrapper `qgis_rs.cli:main` delegates to the
//! same logic via the library crate, so `python -m qgis_rs.cli` and `qgis-cli`
//! behave identically, both at native speed.

use std::process::ExitCode;

fn main() -> ExitCode {
    qgis_cli::main_entry()
}
