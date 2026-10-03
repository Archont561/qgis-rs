//! The transport every qgis-rs binding speaks.
//!
//! A binding does not expose the engine's functions. It exposes exactly one
//! call that takes a request and returns a response, both of them JSON text,
//! and this crate is what those two shapes are. The *wire* is the interface,
//! so adding an operation is a change to one enum rather than a new function
//! signature in PyO3, a new one in NAPI, a new `.pyi` entry, a new `.d.ts`
//! entry and a new release of two packages.
//!
//! # Naming
//!
//! Everything on the wire is `snake_case`, including the operation names. The
//! payloads carry `qgis-render`'s own types — `qgis_render::Extent`,
//! `qgis_render::Tile`, `qgis_render::ProjectInfo` — serialised by the
//! serde derives those types already have, and those derives are `snake_case`.
//! One convention for the whole envelope is worth more than a camelCase
//! envelope wrapped around snake_case contents; the JavaScript client renames
//! at its own edge, which it had to do anyway.
//!
//! # Two version numbers, deliberately not one
//!
//! [`TRANSPORT_VERSION`] is the shape of the envelope below. `qgis_render`'s
//! `VERSION` is the release of the engine. They move independently: a patch
//! release of the engine does not change the envelope, and a new envelope does
//! not imply new geometry.

use serde::{Deserialize, Serialize};
use serde_json::Value;

/// The shape version of this envelope.
///
/// Bumped when a request or response field changes meaning — a new required
/// field, a changed default, a removed operation. An engine that receives a
/// version it does not know answers `ok: false` rather than guessing, so a
/// client built against a future transport fails loudly against an old engine
/// instead of silently reading the wrong field.
///
/// Starts at 1 because this is the first envelope.
pub const TRANSPORT_VERSION: u32 = 1;

/// One request to the engine.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EngineRequest {
    /// The envelope shape the caller speaks. Checked against
    /// [`TRANSPORT_VERSION`].
    pub transport_version: u32,
    /// What to do.
    pub operation: Operation,
    /// The operation's arguments. Defaults to null so an argument-less
    /// operation is a request with one omitted field rather than a
    /// special-cased one.
    #[serde(default)]
    pub payload: Value,
}

impl EngineRequest {
    /// A request in this build's transport version.
    #[must_use]
    pub const fn new(operation: Operation, payload: Value) -> Self {
        Self {
            transport_version: TRANSPORT_VERSION,
            operation,
            payload,
        }
    }
}

/// Everything the engine can be asked to do.
///
/// A closed enum on purpose. An unknown operation is a request that cannot be
/// served and should arrive as one: a typo in an operation name is a mistake a
/// caller can read and fix, whereas an open `Custom(String)` would turn every
/// future engine operation into a silent no-op for every binding compiled
/// before it existed.
///
/// The `describe_*` operations are how a client gets a *derived* value — the
/// width of an extent, the unit of a CRS, the number of levels in a zoom range.
/// They exist so that no client re-implements a rule locally "because it is
/// only arithmetic": that arithmetic is the thing this project is the
/// definition of.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Operation {
    /// Echo the payload back with the engine's name. Proves the boundary is
    /// live without needing any valid domain input.
    Ping,
    /// This build's version, the transport it speaks, its limits and the
    /// operations it serves.
    EngineInfo,
    /// Initialize the standalone native QGIS manager.
    AppInit,
    /// Release all managed QGIS objects and stop the native manager.
    AppShutdown,
    /// Open a managed vector layer and return its opaque integer ID.
    LayerOpen,
    /// Read all supported metadata for a managed vector layer.
    LayerInfo,
    /// Release a managed vector layer from the registry.
    LayerClose,
    /// Read one bounded page of features from a managed vector layer.
    LayerFeatures,
    /// Create a managed vector layer and return its opaque integer ID.
    LayerNew,
    /// Check whether a managed vector layer is valid.
    LayerIsValid,
    /// Read a managed vector layer's display name.
    LayerName,
    /// Read a managed vector layer's feature count.
    LayerFeatureCount,
    /// Read a managed vector layer's CRS authority ID.
    LayerCrsAuthid,
    /// Read a managed vector layer's geometry type name.
    LayerGeometryTypeName,
    /// Read a managed vector layer's copied field metadata.
    LayerFields,
    /// Parse and/or describe an extent: edges, width, height, validity.
    DescribeExtent,
    /// Whether an extent contains a point.
    ExtentContains,
    /// Whether two extents share at least one point.
    ExtentIntersects,
    /// Parse and describe a CRS authority code.
    DescribeCrs,
    /// Parse and describe a zoom level or `min-max` range.
    DescribeZoomRange,
    /// The tile covering a longitude/latitude pair at one zoom level.
    TileFromLonLat,
    /// The EPSG:4326 bounds of one tile.
    TileBounds,
    /// Plan an XYZ pyramid over an extent: per-level ranges and tile counts.
    PlanTiles,
    /// Describe a project file on disk.
    ProjectInfo,
    /// List the layers of a project.
    ProjectLayers,
    /// Render a QGIS project to a path-based image artifact.
    RenderMap,
    /// Export one QGIS vector layer to a path-based feature artifact.
    ExportFeatures,
    /// Legacy pure-engine project render operation.
    RenderProject,
}

impl Operation {
    /// Every operation this transport defines, in wire spelling.
    ///
    /// Used by `engine_info` so a client can discover what the engine it is
    /// talking to actually serves, instead of assuming its own build's list.
    #[must_use]
    pub const fn all() -> &'static [&'static str] {
        &[
            "ping",
            "engine_info",
            "app_init",
            "app_shutdown",
            "layer_open",
            "layer_info",
            "layer_close",
            "layer_features",
            "layer_new",
            "layer_is_valid",
            "layer_name",
            "layer_feature_count",
            "layer_crs_authid",
            "layer_geometry_type_name",
            "layer_fields",
            "describe_extent",
            "extent_contains",
            "extent_intersects",
            "describe_crs",
            "describe_zoom_range",
            "tile_from_lon_lat",
            "tile_bounds",
            "plan_tiles",
            "project_info",
            "project_layers",
            "render_map",
            "export_features",
            "render_project",
        ]
    }
}

/// Arguments for opening a vector layer in the native manager.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LayerOpenRequest {
    pub uri: String,
    pub provider: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
}

/// Arguments shared by layer metadata and close operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct LayerIdRequest {
    pub layer_id: u64,
}

fn default_layer_feature_limit() -> u32 {
    100
}

/// Arguments for one bounded, batched feature page.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct LayerFeaturesRequest {
    pub layer_id: u64,
    #[serde(default)]
    pub offset: u64,
    #[serde(default = "default_layer_feature_limit")]
    pub limit: u32,
}

/// A copied field description returned as part of layer metadata.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LayerFieldInfo {
    pub name: String,
    #[serde(rename = "type")]
    pub type_name: String,
    pub precision: i32,
}

/// The metadata returned by `layer.info`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LayerInfoResponse {
    pub layer_id: u64,
    pub is_valid: bool,
    pub name: String,
    pub feature_count: i64,
    pub crs_authid: String,
    pub geometry_type_name: String,
    pub fields: Vec<LayerFieldInfo>,
}

/// The result returned by `layer.open`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LayerOpenResponse {
    pub layer_id: u64,
    pub is_valid: bool,
    pub name: String,
}

/// The result returned by `layer.close`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LayerCloseResponse {
    pub layer_id: u64,
    pub closed: bool,
}

/// One feature copied into the transport response. No QGIS pointer or Qt
/// value crosses the manager boundary.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LayerFeature {
    pub id: i64,
    pub attributes: Value,
    pub geometry_wkt: String,
}

/// The result returned by one batched `layer.features` request.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LayerFeaturesResponse {
    pub layer_id: u64,
    pub offset: u64,
    pub limit: u32,
    pub next_offset: Option<u64>,
    pub total: i64,
    pub features: Vec<LayerFeature>,
}

/// The result returned by an explicit manager shutdown.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AppShutdownResponse {
    pub shutdown: bool,
    pub released_layer_count: u64,
}

/// Arguments for the native `render_map` operation.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RenderMapRequest {
    pub project: String,
    pub output: String,
    #[serde(default)]
    pub width: Option<u32>,
    #[serde(default)]
    pub height: Option<u32>,
    #[serde(default)]
    pub dpi: Option<f64>,
    #[serde(default)]
    pub crs: Option<String>,
    #[serde(default)]
    pub extent: Option<String>,
    #[serde(default)]
    pub layers: Vec<String>,
    #[serde(default)]
    pub layout: Option<String>,
}

/// The path-based image artifact returned by `render_map`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RenderMapResponse {
    pub path: String,
    pub format: String,
    pub bytes: u64,
    pub width: u32,
    pub height: u32,
}

/// Arguments for the native `export_features` operation.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExportFeaturesRequest {
    pub project: String,
    pub layer: String,
    pub output: String,
    #[serde(default)]
    pub filter: Option<String>,
    #[serde(default)]
    pub bbox: Option<String>,
    #[serde(default)]
    pub fields: Vec<String>,
}

/// The path-based feature artifact returned by `export_features`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExportFeaturesResponse {
    pub path: String,
    pub format: String,
    pub bytes: u64,
    pub layer: String,
    pub feature_count: u64,
}

/// One response from the engine.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EngineResponse {
    /// Always this engine's [`TRANSPORT_VERSION`], even for a request that
    /// carried a different one — the answer is in this engine's dialect,
    /// whatever the question was written in.
    pub transport_version: u32,
    /// Whether the operation succeeded. On `false`, `result` holds the error.
    pub ok: bool,
    /// The operation's answer, or the error.
    pub result: Value,
}

impl EngineResponse {
    /// A response whose operation succeeded.
    #[must_use]
    pub const fn success(result: Value) -> Self {
        Self {
            transport_version: TRANSPORT_VERSION,
            ok: true,
            result,
        }
    }

    /// A response whose operation did not succeed.
    ///
    /// Not a Rust error: the request arrived intact and was understood, so the
    /// engine is *answering*, and a binding that cannot parse a response at all
    /// is a bug worth distinguishing from one that rejected the caller's input.
    #[must_use]
    pub const fn failure(result: Value) -> Self {
        Self {
            transport_version: TRANSPORT_VERSION,
            ok: false,
            result,
        }
    }
}

/// The machine-readable classification carried by every failure.
///
/// A client maps these onto its own language's exceptions — `invalid_extent`
/// is a `ValueError` in Python and a `TypeError`-free plain `Error` in
/// JavaScript, `project_not_found` is a `FileNotFoundError`. Without it every
/// client would have to pattern-match on English error prose, which is the
/// other way the same rule gets written down twice.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ErrorKind {
    /// The request itself could not be read as an [`EngineRequest`].
    InvalidRequest,
    /// The request's `transport_version` is not one this engine serves.
    UnsupportedTransport,
    /// The payload is missing a field, or a field has the wrong type.
    InvalidPayload,
    /// A file or directory could not be read or written.
    Io,
    /// The project file does not exist.
    ProjectNotFound,
    /// The file is neither `.qgs` nor `.qgz`.
    UnsupportedProject,
    /// A string could not be read as `minx,miny,maxx,maxy`.
    InvalidExtent,
    /// A string could not be read as a zoom level or `min-max` range.
    InvalidZoomRange,
    /// The authority code is not shaped like `EPSG:3857`.
    UnknownCrs,
    /// An output path has no recognisable image-format extension.
    UnknownImageFormat,
    /// The operation needs the optional native QGIS backend.
    Unimplemented,
    /// The operation name is not served by the native manager.
    InvalidOperation,
    /// An object ID is missing, stale, or has the wrong type.
    InvalidObjectId,
    /// The native manager must be initialized before this operation.
    NotInitialized,
    /// QGIS rejected an operation or returned an unusable object.
    Qgis,
    /// The native manager caught an unexpected internal failure.
    Internal,
}

impl ErrorKind {
    /// The wire spelling of this kind.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::InvalidRequest => "invalid_request",
            Self::UnsupportedTransport => "unsupported_transport",
            Self::InvalidPayload => "invalid_payload",
            Self::Io => "io",
            Self::ProjectNotFound => "project_not_found",
            Self::UnsupportedProject => "unsupported_project",
            Self::InvalidExtent => "invalid_extent",
            Self::InvalidZoomRange => "invalid_zoom_range",
            Self::UnknownCrs => "unknown_crs",
            Self::UnknownImageFormat => "unknown_image_format",
            Self::Unimplemented => "unimplemented",
            Self::InvalidOperation => "invalid_operation",
            Self::InvalidObjectId => "invalid_object_id",
            Self::NotInitialized => "not_initialized",
            Self::Qgis => "qgis",
            Self::Internal => "internal",
        }
    }
}
