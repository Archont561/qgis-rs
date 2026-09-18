//! `qgis-cli` — the command line for the qgis-rs ecosystem.
//!
//! ```text
//! qgis-cli render map.qgs -o map.png
//! qgis-cli tiles  map.qgs -z 10-14 -b 14,50,15,51 -o tiles/ --dry-run
//! qgis-cli info   map.qgs --json
//! qgis-cli serve  map.qgs --port 8080
//! qgis-cli export map.qgs --layer buildings -o buildings.geojson
//! qgis-cli mcp                       # Model Context Protocol server on stdio
//! ```

use std::process::ExitCode;

fn main() -> ExitCode {
    qgis_cli::main_entry()
}
