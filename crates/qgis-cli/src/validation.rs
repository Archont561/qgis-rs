//! CLI presentation only: domain parsing stays in qgis-render.
use crate::cli::{ValidateArgs, ValidateKind};
use anyhow::{bail, Context, Result};
use clap::ValueEnum;
use qgis_render::{Crs, Extent, Tile, ZoomRange};
use serde_json::{json, Value};

/// Marker for validation refusals; legacy command errors keep exit 1.
///
/// `plan` reuses it rather than adding its own exit-10 category, so malformed
/// input means the same thing whichever pure command refused it.
#[derive(Debug)]
pub(crate) struct InvalidInput(String);

impl InvalidInput {
    pub(crate) fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl std::fmt::Display for InvalidInput {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for InvalidInput {}

pub(crate) fn run(args: ValidateArgs) -> Result<()> {
    let result = normalized(&args);
    let kind = args
        .kind
        .to_possible_value()
        .expect("validation kinds are visible");
    let error = result
        .as_ref()
        .err()
        .map(|error| json!({"code": "invalid_input", "message": error.to_string()}));
    if args.json {
        let report = json!({
            "kind": kind.get_name(), "valid": result.is_ok(),
            "value": result.as_ref().ok(), "error": error,
        });
        println!("{}", serde_json::to_string(&report)?);
    } else if let Ok(value) = &result {
        println!("valid {}: {}", kind.get_name(), value);
    }
    result
        .map(|_| ())
        .map_err(|error| InvalidInput::new(error.to_string()).into())
}

fn normalized(args: &ValidateArgs) -> Result<Value> {
    match args.kind {
        ValidateKind::Crs => {
            let crs = Crs::from_auth_id(&args.value)?;
            Ok(json!({"auth_id": crs.auth_id(), "validation": "syntax_only"}))
        }
        ValidateKind::Tile => {
            let parts: Vec<_> = args.value.split('/').collect();
            let [z, x, y] = parts.as_slice() else {
                bail!("invalid tile: expected z/x/y");
            };
            let coordinate = |text: &str| {
                text.trim()
                    .parse::<u32>()
                    .context("invalid tile: z, x and y must be unsigned 32-bit integers")
            };
            let tile = Tile::new(coordinate(z)?, coordinate(x)?, coordinate(y)?);
            let bounds = tile
                .checked_bounds()
                .context("invalid tile: zoom or XYZ indices are outside the supported domain")?;
            Ok(json!({"tile": tile, "bounds": bounds}))
        }
        ValidateKind::Zoom => Ok(json!(ZoomRange::parse(&args.value)?)),
        ValidateKind::Extent => Ok(json!(Extent::parse(&args.value)?)),
    }
}
