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
    /// Render a project to an image.
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
            "render_project",
        ]
    }
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
    /// The operation needs the QGIS backend, which is not wired up yet.
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
