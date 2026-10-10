//! Read-only process reports. Domain capability ownership stays in the engine.
use crate::cli::DiscoveryArgs;
use anyhow::Result;
use clap::CommandFactory;
use serde_json::json;

pub(crate) fn report(args: DiscoveryArgs) -> Result<()> {
    let engine = qgis_engine::discovery();
    let command = crate::Cli::command();
    let commands: Vec<_> = command
        .get_subcommands()
        .map(|command| command.get_name())
        .collect();
    let diagnosis = "Pure engine is healthy. The QGIS backend is optional; native operations require a qgis-enabled build and working QGIS runtime libraries/configuration. No Python, Node or WebEngine runtime is required by pure commands.";
    let report = json!({
        "status": "healthy",
        "diagnosis": diagnosis,
        "commands": commands,
        "command_note": "Parser surface, not availability: render, export, serve and non-dry-run tiles/batch retain their existing backend gates. Engine capabilities do not imply CLI execution support.",
        "cli": {"name": "qgis-cli", "version": env!("CARGO_PKG_VERSION")},
        "target": {"os": std::env::consts::OS, "arch": std::env::consts::ARCH},
        "engine": engine,
    });
    if args.json {
        println!("{}", serde_json::to_string(&report)?);
    } else {
        println!("qgis-cli {}", env!("CARGO_PKG_VERSION"));
        println!(
            "Target: {} / {}",
            std::env::consts::OS,
            std::env::consts::ARCH
        );
        println!(
            "Engine: {} {}; transport {}",
            engine["engine"].as_str().unwrap_or_default(),
            engine["version"].as_str().unwrap_or_default(),
            engine["transport_version"]
        );
        println!(
            "QGIS backend: {}",
            if engine["backend"]["available"] == true {
                "available"
            } else {
                "unavailable (optional; pure operations remain usable)"
            }
        );
        if let Some(version) = engine["backend"]["qgis_version"].as_str() {
            println!("QGIS version: {version}");
        }
        if engine["backend"]["available"] != true {
            println!("Backend diagnostic: {}", engine["backend"]["error"]);
        }
        println!("Status: healthy. {diagnosis}");
        println!(
            "Commands (parser surface, not availability): {}",
            commands.join(", ")
        );
        println!("{}", report["command_note"].as_str().unwrap_or_default());
        println!("Limits: {}", engine["limits"]);
        for operation in engine["operations"].as_array().into_iter().flatten() {
            println!(
                "  {}: {}",
                operation["name"].as_str().unwrap_or_default(),
                if operation["available"] == true {
                    "available"
                } else {
                    operation["reason"].as_str().unwrap_or("unavailable")
                }
            );
        }
    }
    Ok(())
}
