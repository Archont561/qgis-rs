//! The argument shape of every operation, in one file.
//!
//! Each struct here is the complete definition of what an operation accepts, so
//! "what do I send?" is answered by reading this file rather than by reading a
//! `match` arm. They are deserialised with serde, which means a missing field
//! or a wrong type is reported as `invalid_payload` with serde's own message —
//! the engine never has to hand-write "expected a number".

use std::path::PathBuf;

use qgis_render::{Crs, Error, Extent, RenderSettings, Tile, ZoomRange};
use serde::Deserialize;

/// An extent, given either as the `minx,miny,maxx,maxy` text a CLI accepts or
/// as the four edges.
///
/// Untagged on purpose: a client holding an `Extent` object sends the object,
/// a client holding what a user typed sends the string, and neither has to know
/// about the other's form. Parsing the string is `Extent::parse`, so the one
/// implementation of that grammar stays in `qgis-render`.
#[derive(Debug, Clone, Deserialize)]
#[serde(untagged)]
pub enum ExtentValue {
    /// `"14,50,15,51"`.
    Text(String),
    /// `{"min_x": 14, "min_y": 50, "max_x": 15, "max_y": 51}`.
    Edges(Extent),
}

impl ExtentValue {
    /// Turn either form into a validated extent.
    ///
    /// # Errors
    ///
    /// [`Error::InvalidExtent`] when the text does not parse, or when the four
    /// edges are not finite and ordered — the object form is checked too, so a
    /// client cannot route around the parser by sending edges directly.
    pub fn resolve(&self) -> Result<Extent, Error> {
        match self {
            Self::Text(text) => Extent::parse(text),
            Self::Edges(extent) if extent.is_valid() => Ok(*extent),
            Self::Edges(extent) => Err(Error::InvalidExtent {
                value: extent.to_string(),
            }),
        }
    }
}

/// A zoom range, given as `12`, `"10-14"`, or `{"min": 10, "max": 14}`.
///
/// Three forms rather than one because all three already exist in the project:
/// a number is what a tile server has, the text is what `-z 10-14` gives, and
/// the object is what a client that already parsed one holds.
#[derive(Debug, Clone, Deserialize)]
#[serde(untagged)]
pub enum ZoomValue {
    /// A single level, as a number.
    Level(u32),
    /// `"12"` or `"10-14"`.
    Text(String),
    /// `{"min": 10, "max": 14}`.
    Range(ZoomRange),
}

impl ZoomValue {
    /// Turn any of the three forms into a validated range.
    ///
    /// # Errors
    ///
    /// [`Error::InvalidZoomRange`] when the text does not parse, or when the
    /// range is reversed or deeper than `qgis_render::MAX_ZOOM`.
    pub fn resolve(&self) -> Result<ZoomRange, Error> {
        match self {
            Self::Level(level) => ZoomRange::new(*level, *level),
            Self::Text(text) => ZoomRange::parse(text),
            Self::Range(range) => ZoomRange::new(range.min, range.max),
        }
    }
}

/// `describe_extent`.
#[derive(Debug, Clone, Deserialize)]
pub struct ExtentInput {
    /// The extent to describe.
    pub extent: ExtentValue,
}

impl ExtentInput {
    /// The validated extent.
    ///
    /// # Errors
    ///
    /// Whatever [`ExtentValue::resolve`] reports.
    pub fn resolve(&self) -> Result<Extent, Error> {
        self.extent.resolve()
    }
}

/// `extent_contains`.
#[derive(Debug, Clone, Deserialize)]
pub struct ExtentContains {
    /// The extent to test against.
    pub extent: ExtentValue,
    /// Point x, in the extent's own CRS.
    pub x: f64,
    /// Point y, in the extent's own CRS.
    pub y: f64,
}

/// `extent_intersects`.
#[derive(Debug, Clone, Deserialize)]
pub struct ExtentIntersects {
    /// The first extent.
    pub extent: ExtentValue,
    /// The second extent.
    pub other: ExtentValue,
}

/// `describe_crs` — and anything else whose whole input is one string.
#[derive(Debug, Clone, Deserialize)]
pub struct TextInput {
    /// The text to parse, for example `EPSG:3857`.
    pub text: String,
}

/// `describe_zoom_range`.
#[derive(Debug, Clone, Deserialize)]
pub struct ZoomInput {
    /// The zoom levels to describe.
    pub zooms: ZoomValue,
}

impl ZoomInput {
    /// The validated range.
    ///
    /// # Errors
    ///
    /// Whatever [`ZoomValue::resolve`] reports.
    pub fn resolve(&self) -> Result<ZoomRange, Error> {
        self.zooms.resolve()
    }
}

/// `tile_from_lon_lat`.
#[derive(Debug, Clone, Copy, Deserialize)]
pub struct TileFromLonLat {
    /// Zoom level.
    pub z: u32,
    /// Longitude in EPSG:4326.
    pub lon: f64,
    /// Latitude in EPSG:4326; clamped to the Web Mercator limit, as every tile
    /// client does.
    pub lat: f64,
}

/// `tile_bounds`.
#[derive(Debug, Clone, Copy, Deserialize)]
pub struct TileBounds {
    /// The tile, as `{"z": 10, "x": 551, "y": 342}`.
    pub tile: Tile,
}

/// `plan_tiles`.
#[derive(Debug, Clone, Deserialize)]
pub struct PlanTiles {
    /// The area to cover, in EPSG:4326.
    pub bounds: ExtentValue,
    /// The levels to cover it at.
    pub zooms: ZoomValue,
    /// Also enumerate every tile, not just count them. Off by default: the
    /// counts are what a dry run needs, and the enumeration of a deep pyramid
    /// is large enough that a caller should have to ask for it.
    #[serde(default)]
    pub include_tiles: bool,
}

/// `project_info`, `project_layers`.
#[derive(Debug, Clone, Deserialize)]
pub struct ProjectPath {
    /// Path to a `.qgs` or `.qgz` file.
    pub path: PathBuf,
}

/// `render_project`.
///
/// The optional fields mirror [`RenderSettings`]' builders exactly; omitting one
/// leaves the default that `RenderSettings::new` chose, so the defaults are
/// stated once, in `qgis-render`.
#[derive(Debug, Clone, Deserialize)]
pub struct RenderProject {
    /// Path to the project to render.
    pub path: PathBuf,
    /// Where the image is written. The format is inferred from its extension.
    pub output: PathBuf,
    /// Image width in pixels.
    #[serde(default)]
    pub width: Option<u32>,
    /// Image height in pixels.
    #[serde(default)]
    pub height: Option<u32>,
    /// Resolution in dots per inch.
    #[serde(default)]
    pub dpi: Option<f64>,
    /// CRS to render in; omitted keeps the project CRS.
    #[serde(default)]
    pub crs: Option<String>,
    /// Area to render; omitted uses the full extent.
    #[serde(default)]
    pub extent: Option<ExtentValue>,
    /// Layers to draw; empty means all of them.
    #[serde(default)]
    pub layers: Vec<String>,
    /// Print layout to render instead of the map canvas.
    #[serde(default)]
    pub layout: Option<String>,
}

impl RenderProject {
    /// Build the settings this request describes.
    ///
    /// # Errors
    ///
    /// [`Error::UnknownImageFormat`] when the output extension is not a
    /// supported format, [`Error::UnknownCrs`] for a malformed authority code,
    /// and [`Error::InvalidExtent`] for an unparseable extent.
    pub fn into_settings(self) -> Result<RenderSettings, Error> {
        let mut settings = RenderSettings::new(&self.output)?;
        if let (Some(width), Some(height)) = (self.width, self.height) {
            settings = settings.with_size(width, height);
        } else {
            if let Some(width) = self.width {
                settings.width = width;
            }
            if let Some(height) = self.height {
                settings.height = height;
            }
        }
        if let Some(dpi) = self.dpi {
            settings = settings.with_dpi(dpi);
        }
        if let Some(crs) = self.crs {
            settings = settings.with_crs(Crs::from_auth_id(&crs)?);
        }
        if let Some(extent) = self.extent {
            settings = settings.with_extent(extent.resolve()?);
        }
        if !self.layers.is_empty() {
            settings = settings.with_layers(self.layers);
        }
        if let Some(layout) = self.layout {
            settings = settings.with_layout(layout);
        }
        Ok(settings)
    }
}
