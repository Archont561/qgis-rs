//! XYZ ("slippy map") tile pyramids.
//!
//! Everything here is pure geometry: no tiles are rendered, they are counted
//! and enumerated. That is what `qgis-cli tiles --dry-run` and the `plan_tiles`
//! MCP tool are built on.

use crate::error::{Error, Result};
use crate::extent::Extent;

/// The latitude beyond which the Web Mercator projection is undefined.
pub const MAX_LATITUDE: f64 = 85.051_128_779_806_6;

/// The deepest zoom level the CLI will plan for.
pub const MAX_ZOOM: u32 = 22;

/// One tile in an XYZ pyramid.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct Tile {
    /// Zoom level.
    pub z: u32,
    /// Column, from the west.
    pub x: u32,
    /// Row, from the north.
    pub y: u32,
}

impl Tile {
    /// Build a tile from its three coordinates.
    #[must_use]
    pub const fn new(z: u32, x: u32, y: u32) -> Self {
        Self { z, x, y }
    }

    /// How many tiles a full pyramid level holds.
    #[must_use]
    pub const fn tiles_at_zoom(z: u32) -> u64 {
        let side = 1u64 << z;
        side * side
    }

    /// The tile covering a longitude/latitude pair.
    ///
    /// Latitudes outside [`MAX_LATITUDE`] are clamped, matching what every tile
    /// client does.
    #[must_use]
    pub fn from_lon_lat(z: u32, longitude: f64, latitude: f64) -> Self {
        let side = tiles_per_side(z) as f64;
        let x = ((longitude + 180.0) / 360.0 * side).floor();
        let y = latitude_to_y(z, latitude);
        Self {
            z,
            x: clamp_index(x, side) as u32,
            y: clamp_index(y, side) as u32,
        }
    }

    /// The tile's extent in EPSG:4326.
    #[must_use]
    pub fn bounds(&self) -> Extent {
        let side = tiles_per_side(self.z) as f64;
        Extent::new(
            x_to_longitude(self.x, side),
            y_to_latitude(self.y + 1, side),
            x_to_longitude(self.x + 1, side),
            y_to_latitude(self.y, side),
        )
    }
}

/// An inclusive range of zoom levels.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct ZoomRange {
    /// Shallowest zoom level.
    pub min: u32,
    /// Deepest zoom level.
    pub max: u32,
}

impl ZoomRange {
    /// Build a range, checking that it is ordered and not absurdly deep.
    ///
    /// # Errors
    ///
    /// Returns [`Error::InvalidZoomRange`] when `min > max` or when `max`
    /// exceeds [`MAX_ZOOM`].
    pub fn new(min: u32, max: u32) -> Result<Self> {
        if min > max || max > MAX_ZOOM {
            return Err(Error::InvalidZoomRange {
                value: format!("{min}-{max}"),
            });
        }
        Ok(Self { min, max })
    }

    /// Parse `12` or `10-14`.
    ///
    /// # Errors
    ///
    /// Returns [`Error::InvalidZoomRange`] for anything else.
    pub fn parse(text: &str) -> Result<Self> {
        let invalid = || Error::InvalidZoomRange {
            value: text.to_string(),
        };
        let trimmed = text.trim();
        if let Some((low, high)) = trimmed.split_once('-') {
            let min = low.trim().parse::<u32>().map_err(|_| invalid())?;
            let max = high.trim().parse::<u32>().map_err(|_| invalid())?;
            return Self::new(min, max).map_err(|_| invalid());
        }
        let single = trimmed.parse::<u32>().map_err(|_| invalid())?;
        Self::new(single, single).map_err(|_| invalid())
    }

    /// How many zoom levels the range covers.
    #[must_use]
    pub const fn count(&self) -> u32 {
        self.max - self.min + 1
    }

    /// Iterate the zoom levels, shallowest first.
    #[must_use]
    pub fn iter(&self) -> std::ops::RangeInclusive<u32> {
        self.min..=self.max
    }
}

/// The tile columns and rows that cover an extent at one zoom level.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct ZoomLevelPlan {
    /// The zoom level this row describes.
    pub zoom: u32,
    /// First (westernmost) column.
    pub x_min: u32,
    /// Last (easternmost) column.
    pub x_max: u32,
    /// First (northernmost) row.
    pub y_min: u32,
    /// Last (southernmost) row.
    pub y_max: u32,
}

impl ZoomLevelPlan {
    /// How many tiles this level contributes.
    #[must_use]
    pub fn tile_count(&self) -> u64 {
        u64::from(self.x_max - self.x_min + 1) * u64::from(self.y_max - self.y_min + 1)
    }
}

/// Every tile that covers an EPSG:4326 extent between two zoom levels.
#[derive(Debug, Clone, Copy, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct TilePlan {
    /// The area to cover, in EPSG:4326.
    pub bounds: Extent,
    /// The zoom levels to cover it at.
    pub zooms: ZoomRange,
}

impl TilePlan {
    /// Plan a tile pyramid over `bounds`.
    ///
    /// # Errors
    ///
    /// Returns [`Error::InvalidExtent`] when `bounds` is not ordered.
    pub fn new(bounds: Extent, zooms: ZoomRange) -> Result<Self> {
        if !bounds.is_valid() {
            return Err(Error::InvalidExtent {
                value: bounds.to_string(),
            });
        }
        Ok(Self { bounds, zooms })
    }

    /// The tile range at a single zoom level.
    #[must_use]
    pub fn level(&self, zoom: u32) -> ZoomLevelPlan {
        let side = tiles_per_side(zoom) as f64;
        let x_min = clamp_index(((self.bounds.min_x + 180.0) / 360.0 * side).floor(), side);
        let x_max = clamp_index(((self.bounds.max_x + 180.0) / 360.0 * side).floor(), side);
        let y_min = clamp_index(latitude_to_y(zoom, self.bounds.max_y), side);
        let y_max = clamp_index(latitude_to_y(zoom, self.bounds.min_y), side);
        ZoomLevelPlan {
            zoom,
            x_min: x_min as u32,
            x_max: x_max as u32,
            y_min: y_min as u32,
            y_max: y_max as u32,
        }
    }

    /// One row per zoom level, shallowest first.
    #[must_use]
    pub fn levels(&self) -> Vec<ZoomLevelPlan> {
        self.zooms.iter().map(|zoom| self.level(zoom)).collect()
    }

    /// Total number of tiles across every zoom level.
    #[must_use]
    pub fn tile_count(&self) -> u64 {
        self.levels().iter().map(ZoomLevelPlan::tile_count).sum()
    }

    /// Every tile in the plan, level by level.
    pub fn iter(&self) -> impl Iterator<Item = Tile> + '_ {
        self.levels().into_iter().flat_map(|level| {
            (level.y_min..=level.y_max).flat_map(move |y| {
                (level.x_min..=level.x_max).map(move |x| Tile::new(level.zoom, x, y))
            })
        })
    }
}

/// Tiles per side of the pyramid at `zoom` (`2^zoom`).
#[must_use]
pub const fn tiles_per_side(zoom: u32) -> u64 {
    1u64 << zoom
}

fn latitude_to_y(zoom: u32, latitude: f64) -> f64 {
    let side = tiles_per_side(zoom) as f64;
    let clamped = latitude.clamp(-MAX_LATITUDE, MAX_LATITUDE).to_radians();
    let mercator = (clamped.tan() + 1.0 / clamped.cos()).ln();
    (1.0 - mercator / std::f64::consts::PI) / 2.0 * side
}

fn x_to_longitude(x: u32, side: f64) -> f64 {
    f64::from(x) / side * 360.0 - 180.0
}

fn y_to_latitude(y: u32, side: f64) -> f64 {
    let n = std::f64::consts::PI * (1.0 - 2.0 * f64::from(y) / side);
    n.sinh().atan().to_degrees()
}

fn clamp_index(value: f64, side: f64) -> f64 {
    value.clamp(0.0, side - 1.0)
}
