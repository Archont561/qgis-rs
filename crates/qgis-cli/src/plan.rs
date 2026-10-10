//! Deterministic planning: pure geometry over an extent, with no project.
//!
//! `qgis-cli tiles <project> --dry-run` also counts a pyramid, but it opens
//! the project first, so it needs a `.qgs`/`.qgz` on disk even though it never
//! reads it. Planning does not: the numbers come from [`qgis_render::TilePlan`]
//! alone, which is why nothing here initialises a backend or writes a file.
use crate::cli::{PlanArgs, PlanCommand, TilesPlanArgs};
use crate::validation::InvalidInput;
use anyhow::{Context, Result};
use qgis_render::{Extent, TilePlan, TilePlanReport, ZoomRange};
use serde_json::json;

pub(crate) fn run(args: PlanArgs) -> Result<()> {
    match args.command {
        PlanCommand::Tiles(args) => tiles(args),
        PlanCommand::Batch(args) => crate::batch_plan::run(args),
    }
}

fn tiles(args: TilesPlanArgs) -> Result<()> {
    let result = parsed(&args);

    // `--json` keeps stdout a single parseable document on failure too, and
    // the reason still goes to stderr through `main_entry`.
    if args.json {
        let payload = match &result {
            Ok(report) => serde_json::to_value(report)?,
            Err(error) => json!({
                "error": {"code": "invalid_input", "message": format!("{error:#}")}
            }),
        };
        println!("{}", serde_json::to_string(&payload)?);
    }

    let report = result.map_err(|error| InvalidInput::new(format!("{error:#}")))?;
    if !args.json {
        for level in &report.levels {
            println!(
                "z={:<3} x {}..{}  y {}..{}  {} tiles",
                level.zoom, level.x_min, level.x_max, level.y_min, level.y_max, level.tile_count
            );
        }
        println!(
            "{} tiles across zoom levels {}-{}",
            report.tile_count, report.zooms.min, report.zooms.max
        );
    }
    Ok(())
}

/// Parse the flags into a plan, or say which flag was unreadable.
fn parsed(args: &TilesPlanArgs) -> Result<TilePlanReport> {
    let bounds = Extent::parse(&args.bounds)
        .with_context(|| format!("cannot read --bounds {:?}", args.bounds))?;
    let zooms = ZoomRange::parse(&args.zoom)
        .with_context(|| format!("cannot read --zoom {:?}", args.zoom))?;
    let plan = TilePlan::new(bounds, zooms)?;
    Ok(plan.report())
}
