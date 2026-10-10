//! Read-only tile planning over the existing batch CSV vocabulary.
use crate::cli::BatchPlanArgs;
use crate::commands::parse_extent_rows;
use crate::inspection::Failure;
use anyhow::Result;
use qgis_render::{TilePlan, TilePlanReport, ZoomRange};
use serde_json::{json, Value};
use std::path::Path;

struct BatchReport {
    extents: Vec<(String, TilePlanReport)>,
    tile_count: u64,
}

impl BatchReport {
    fn json(&self) -> Value {
        json!({
            "extent_count": self.extents.len(),
            "tile_count": self.tile_count,
            "extents": self.extents.iter().map(|(name, plan)| {
                json!({"name": name, "plan": plan})
            }).collect::<Vec<_>>(),
        })
    }
}

pub(crate) fn run(args: BatchPlanArgs) -> Result<()> {
    let result = parsed(&args);
    if args.json {
        let report = match &result {
            Ok(report) => report.json(),
            Err(error) => json!({
                "error": {"code": error.code(), "message": error.to_string()}
            }),
        };
        println!("{report}");
    }
    let report = result?;
    if !args.json {
        for (name, plan) in &report.extents {
            println!(
                "{name}: {} tiles across zoom levels {}-{}",
                plan.tile_count, plan.zooms.min, plan.zooms.max
            );
        }
        println!(
            "{} tiles across {} extents",
            report.tile_count,
            report.extents.len()
        );
    }
    Ok(())
}

fn parsed(args: &BatchPlanArgs) -> Result<BatchReport, Failure> {
    let zooms = ZoomRange::parse(&args.zoom).map_err(|error| {
        Failure::InvalidInput(format!("cannot read --zoom {:?}: {error}", args.zoom))
    })?;
    let metadata = std::fs::metadata(&args.extents)
        .map_err(|error| filesystem_failure(&args.extents, error))?;
    if !metadata.is_file() {
        return Err(Failure::InvalidInput(format!(
            "not a regular CSV file: {}",
            args.extents.display()
        )));
    }
    let text = std::fs::read_to_string(&args.extents).map_err(|error| {
        if error.kind() == std::io::ErrorKind::InvalidData {
            Failure::InvalidInput(format!(
                "cannot read UTF-8 CSV {}: {error}",
                args.extents.display()
            ))
        } else {
            filesystem_failure(&args.extents, error)
        }
    })?;
    let rows = parse_extent_rows(&text).map_err(|error| {
        Failure::InvalidInput(format!(
            "cannot parse {}: {error:#}",
            args.extents.display()
        ))
    })?;
    let mut extents = Vec::with_capacity(rows.len());
    let mut tile_count = 0u64;
    for (name, bounds) in rows {
        let plan = TilePlan::new(bounds, zooms)
            .map_err(|error| Failure::InvalidInput(error.to_string()))?
            .report();
        tile_count = tile_count.checked_add(plan.tile_count).ok_or_else(|| {
            Failure::InvalidInput(
                "batch tile count exceeds the supported integer range".to_string(),
            )
        })?;
        extents.push((name, plan));
    }
    Ok(BatchReport {
        extents,
        tile_count,
    })
}

fn filesystem_failure(path: &Path, error: std::io::Error) -> Failure {
    if error.kind() == std::io::ErrorKind::NotFound {
        Failure::MissingExtents(path.to_path_buf())
    } else {
        Failure::Filesystem(format!("cannot read CSV input {}: {error}", path.display()))
    }
}
