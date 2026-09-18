//! `qgis-cli` library — CLI definition and command dispatch.
//!
//! The binary in `main.rs` is a thin wrapper around this library so that
//! other crates (e.g. the Python package `qgis-rs`) can reuse the same
//! argument parsing and command implementations and ship the identical
//! native-speed CLI.

pub mod cli;
pub mod commands;

pub use cli::{Cli, Command};
pub use commands::run;

use clap::Parser as _;
use std::process::ExitCode;

/// Parse arguments from the process environment and run the selected command.
///
/// This is the entry point used by both the standalone `qgis-cli` binary and
/// the `qgis_rs` Python package's `qgis-cli` console script wrapper.
pub fn main_entry() -> ExitCode {
    let cli = Cli::parse();
    match run(cli.command) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("qgis-cli: {error:#}");
            ExitCode::FAILURE
        }
    }
}
