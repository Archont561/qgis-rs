//! qgis-cli binary for npm package — same as crates/qgis-cli but built for Node distribution

use std::process::ExitCode;

fn main() -> ExitCode {
    qgis_cli::main_entry()
}
