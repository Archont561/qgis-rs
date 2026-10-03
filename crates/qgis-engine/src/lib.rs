//! The dispatcher behind [`invoke`].
//!
//! Everything a binding can ask qgis-rs to do is one arm of one match, and each
//! arm calls into `qgis-render` and hands back JSON. No geometry rule lives
//! here: this crate translates a wire request into a domain call. If a rule
//! would have to be stated twice — once here and once in `qgis-render` — it is
//! stated in `qgis-render` and this arm reads it.
//!
//! ```
//! use qgis_engine::invoke;
//!
//! let response = invoke(r#"{"transport_version":1,"operation":"ping","payload":42}"#);
//! assert!(response.contains("\"ok\":true"));
//! ```

mod payload;

// Re-exported, not merely imported: a binding, a test or the CLI can name the
// transport it was built against without adding a second dependency edge.
pub use qgis_protocol::{EngineRequest, EngineResponse, ErrorKind, Operation, TRANSPORT_VERSION};
use qgis_render::{Crs, Error, Project, Tile, TilePlan, ZoomLevelPlan};
use serde::de::DeserializeOwned;
use serde_json::{json, Value};

use crate::payload::{
    ExtentContains, ExtentInput, ExtentIntersects, PlanTiles, ProjectPath, RenderProject,
    TextInput, TileBounds, TileFromLonLat, ZoomInput,
};

/// The name this engine answers `ping` with.
pub const ENGINE: &str = "qgis-engine";

/// Run one request and return one response, both as JSON text.
///
/// A string in and a string out, rather than typed values, because that is the
/// entire contract with the bindings: they pass text across an FFI boundary
/// they do not share types with. Returning `String` rather than an
/// `EngineResponse` is also what forces every answer to be *serialisable* — a
/// future field that cannot cross the wire fails in this function, at the
/// boundary, rather than in whichever binding happened to run first.
///
/// # Panics
///
/// If an [`EngineResponse`] cannot be serialised. Every value this crate
/// constructs is plain JSON, so that is a bug in this file rather than a
/// condition a caller can provoke; the alternative is a `Result` every binding
/// would unwrap anyway.
#[must_use]
pub fn invoke(request_json: &str) -> String {
    let response = match serde_json::from_str::<EngineRequest>(request_json) {
        Ok(request) if request.transport_version == TRANSPORT_VERSION => run(&request),
        Ok(request) => failure(
            ErrorKind::UnsupportedTransport,
            format!(
                "this engine speaks transport version {TRANSPORT_VERSION}, the request declared {}",
                request.transport_version
            ),
            json!({ "supported": TRANSPORT_VERSION, "received": request.transport_version }),
        ),
        Err(error) => failure(
            ErrorKind::InvalidRequest,
            "request is not a transport envelope",
            json!({ "detail": error.to_string() }),
        ),
    };
    serde_json::to_string(&response).expect("engine responses are serialisable")
}

/// Dispatch one request whose transport version has already been accepted.
fn run(request: &EngineRequest) -> EngineResponse {
    let payload = &request.payload;
    match request.operation {
        // The payload is echoed rather than interpreted, which is the whole
        // test: a value that survives the round trip proves the boundary did
        // not truncate, re-encode or reinterpret it.
        Operation::Ping => success(json!({ "engine": ENGINE, "echo": payload })),
        Operation::EngineInfo => success(json!({
            "engine": ENGINE,
            "version": qgis_render::VERSION,
            "transport_version": TRANSPORT_VERSION,
            "max_zoom": qgis_render::MAX_ZOOM,
            "max_latitude": qgis_render::MAX_LATITUDE,
            "operations": Operation::all(),
        })),
        Operation::AppInit
        | Operation::AppShutdown
        | Operation::LayerOpen
        | Operation::LayerInfo
        | Operation::LayerClose
        | Operation::LayerFeatures
        | Operation::LayerNew
        | Operation::LayerIsValid
        | Operation::LayerName
        | Operation::LayerFeatureCount
        | Operation::LayerCrsAuthid
        | Operation::LayerGeometryTypeName
        | Operation::LayerFields => failure(
            ErrorKind::Unimplemented,
            "operation requires the native QGIS manager",
            Value::Null,
        ),
        Operation::DescribeExtent => with_payload(payload, |input: ExtentInput| {
            let extent = input.resolve()?;
            Ok(json!({
                "extent": extent,
                "width": extent.width(),
                "height": extent.height(),
                "is_valid": extent.is_valid(),
            }))
        }),
        Operation::ExtentContains => with_payload(payload, |input: ExtentContains| {
            let extent = input.extent.resolve()?;
            Ok(json!({ "contains": extent.contains(input.x, input.y) }))
        }),
        Operation::ExtentIntersects => with_payload(payload, |input: ExtentIntersects| {
            let extent = input.extent.resolve()?;
            let other = input.other.resolve()?;
            Ok(json!({ "intersects": extent.intersects(&other) }))
        }),
        Operation::DescribeCrs => with_payload(payload, |input: TextInput| {
            let crs = Crs::from_auth_id(&input.text)?;
            Ok(json!({
                "auth_id": crs.auth_id(),
                "name": crs.name(),
                "units": crs.units(),
                "is_geographic": crs.is_geographic(),
            }))
        }),
        Operation::DescribeZoomRange => with_payload(payload, |input: ZoomInput| {
            let zooms = input.resolve()?;
            Ok(json!({ "zooms": zooms, "count": zooms.count() }))
        }),
        Operation::TileFromLonLat => with_payload(payload, |input: TileFromLonLat| {
            let tile = Tile::from_lon_lat(input.z, input.lon, input.lat);
            Ok(json!({ "tile": tile, "bounds": tile.bounds() }))
        }),
        Operation::TileBounds => with_payload(payload, |input: TileBounds| {
            Ok(json!({ "bounds": input.tile.bounds() }))
        }),
        Operation::PlanTiles => with_payload(payload, plan_tiles),
        Operation::ProjectInfo => with_payload(payload, |input: ProjectPath| {
            Ok(json!(Project::open(&input.path)?.info()?))
        }),
        Operation::ProjectLayers => with_payload(payload, |input: ProjectPath| {
            Ok(json!({ "layers": Project::open(&input.path)?.layers()? }))
        }),
        Operation::RenderProject => with_payload(payload, |input: RenderProject| {
            let project = Project::open(&input.path)?;
            let settings = input.into_settings()?;
            Ok(json!(project.render(&settings)?))
        }),
    }
}

/// Plan an XYZ pyramid and report it level by level.
///
/// `tile_count` is included per level because [`ZoomLevelPlan`] computes it
/// rather than storing it, and a client that recomputed it from the x/y ranges
/// would be the second implementation of a one-line rule.
fn plan_tiles(input: PlanTiles) -> Result<Value, Error> {
    let bounds = input.bounds.resolve()?;
    let zooms = input.zooms.resolve()?;
    let plan = TilePlan::new(bounds, zooms)?;
    let levels: Vec<Value> = plan.levels().iter().map(level_json).collect();
    let mut result = json!({
        "bounds": plan.bounds,
        "zooms": plan.zooms,
        "tile_count": plan.tile_count(),
        "levels": levels,
    });
    // Enumerating every tile is opt-in: a five-level plan over a city is 4568
    // tiles, and a pyramid a client only wants the *count* of should not pay
    // to serialise them. `qgis-cli tiles --dry-run` asks for the counts only.
    if input.include_tiles {
        result["tiles"] = json!(plan.iter().collect::<Vec<Tile>>());
    }
    Ok(result)
}

fn level_json(level: &ZoomLevelPlan) -> Value {
    json!({
        "zoom": level.zoom,
        "x_min": level.x_min,
        "x_max": level.x_max,
        "y_min": level.y_min,
        "y_max": level.y_max,
        "tile_count": level.tile_count(),
    })
}

/// Deserialise a payload and run an operation over it.
///
/// Both failure modes a payload has — "this is not the shape the operation
/// takes" and "the engine refused the values in it" — are answered as
/// responses with a `kind`, never as a panic or a Rust error escaping the
/// boundary.
fn with_payload<P, F>(payload: &Value, operation: F) -> EngineResponse
where
    P: DeserializeOwned,
    F: FnOnce(P) -> Result<Value, Error>,
{
    // `Value::Null` for an omitted payload: an operation whose fields all have
    // defaults must still run when the caller sent nothing at all.
    let input = match serde_json::from_value::<P>(payload.clone()) {
        Ok(input) => input,
        Err(error) => {
            return failure(
                ErrorKind::InvalidPayload,
                "payload does not match the operation",
                json!({ "detail": error.to_string() }),
            )
        }
    };
    match operation(input) {
        Ok(result) => success(result),
        Err(error) => failure(kind_of(&error), error.to_string(), Value::Null),
    }
}

/// Classify a domain error for a client that has to choose an exception type.
///
/// The mapping lives here, next to the boundary, because `qgis-render` has no
/// opinion about transports and a client has no access to the Rust enum.
const fn kind_of(error: &Error) -> ErrorKind {
    match error {
        Error::Io { .. } => ErrorKind::Io,
        Error::ProjectNotFound { .. } => ErrorKind::ProjectNotFound,
        Error::UnsupportedProject { .. } => ErrorKind::UnsupportedProject,
        Error::InvalidExtent { .. } => ErrorKind::InvalidExtent,
        Error::InvalidZoomRange { .. } => ErrorKind::InvalidZoomRange,
        Error::UnknownCrs { .. } => ErrorKind::UnknownCrs,
        Error::UnknownImageFormat { .. } => ErrorKind::UnknownImageFormat,
        Error::Unimplemented { .. } => ErrorKind::Unimplemented,
    }
}

fn success(result: Value) -> EngineResponse {
    EngineResponse::success(result)
}

/// Every failure has the same three parts: a kind a client can branch on, the
/// engine's own wording, and whatever detail the specific failure has.
fn failure(kind: ErrorKind, message: impl Into<String>, detail: Value) -> EngineResponse {
    let mut result = json!({ "kind": kind, "error": message.into() });
    if let Value::Object(extra) = detail {
        for (key, value) in extra {
            result[key] = value;
        }
    }
    EngineResponse::failure(result)
}

/// Build a request the way a client would, for tests and for callers that have
/// typed values rather than JSON text in hand.
///
/// # Panics
///
/// If `payload` cannot be serialised, which for the `serde_json::json!` values
/// every caller passes cannot happen.
#[must_use]
pub fn request(operation: Operation, payload: Value) -> String {
    serde_json::to_string(&EngineRequest::new(operation, payload))
        .expect("engine requests are serialisable")
}

/// Convenience for callers that already hold typed values: build the request,
/// invoke, and hand back the decoded response.
///
/// # Panics
///
/// If the engine's own response does not parse, which would be a bug in
/// [`invoke`].
#[must_use]
pub fn call(operation: Operation, payload: Value) -> EngineResponse {
    serde_json::from_str(&invoke(&request(operation, payload)))
        .expect("engine answers its own dialect")
}
