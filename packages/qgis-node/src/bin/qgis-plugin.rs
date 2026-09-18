//! qgis-plugin binary for npm package

use std::process::ExitCode;
use clap::Parser;

#[derive(Debug, Parser)]
#[command(name = "qgis-plugin", version, about = "QGIS plugin SDK — native speed")]
struct Cli {
    #[arg(long)]
    version: bool,
    #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
    args: Vec<String>,
}

fn main() -> ExitCode {
    // For npm package, we delegate to qgis-sdk crate's CLI if available
    // Simplified: just print version and help, actual logic in qgis-sdk crate
    let args: Vec<String> = std::env::args().collect();
    if args.len() > 1 && (args[1] == "--version" || args[1] == "-V" || args[1] == "version") {
        println!("qgis-plugin {} (from qgis-rs npm, Rust-native)", env!("CARGO_PKG_VERSION"));
        return ExitCode::SUCCESS;
    }
    
    // Try to find qgis-sdk binary logic — for now, just show help
    if args.len() == 1 || args.iter().any(|a| a == "--help" || a == "-h") {
        println!("qgis-plugin {} — QGIS plugin SDK (Rust-native)", env!("CARGO_PKG_VERSION"));
        println!();
        println!("Usage: qgis-plugin <command> [options]");
        println!();
        println!("Commands:");
        println!("  new       Scaffold a new plugin");
        println!("  build     Build plugin");
        println!("  test      Run tests");
        println!("  install   Install into QGIS");
        println!("  dev       Watch mode");
        println!("  package   Create .zip");
        println!("  validate  Check structure");
        println!("  info      Show plugin info");
        println!("  version   Print version");
        println!();
        println!("For full CLI, install qgis-sdk Python package or use npx qgis-rs");
        return ExitCode::SUCCESS;
    }
    
    eprintln!("qgis-plugin: full functionality requires qgis-sdk Rust crate");
    eprintln!("qgis-plugin: install via: npm install qgis-rs && npx qgis-plugin --help");
    ExitCode::FAILURE
}
