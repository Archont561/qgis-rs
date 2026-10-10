//! Honest discovery of this dispatcher, not just the protocol vocabulary.
use crate::{native_operation, Operation, ENGINE, TRANSPORT_VERSION};
use serde_json::{json, Value};

/// Describe the engine, enforced domain limits, and callable operations.
///
/// Native builds probe the manager on its owner thread. A protocol operation
/// is not advertised as callable merely because the native manager knows it:
/// this report describes routes actually implemented by this engine.
///
/// # Panics
///
/// Panics if the protocol catalogue contains a name its own enum cannot decode.
#[must_use]
pub fn discovery() -> Value {
    let native = native_operation(Operation::ApiDescribe, &Value::Null);
    let ready = native.ok;
    let manifest = &native.result;
    let backend = json!({
        "name": "qgis-native-manager",
        "available": ready,
        "compiled": cfg!(feature = "qgis"),
        "error": if ready { Value::Null } else { manifest.clone() },
        "qgis_version": manifest.get("qgis_version"),
        "reason": if ready { Value::Null } else { json!("QGIS backend is unavailable; pure operations remain usable") },
    });
    let operations: Vec<Value> = Operation::all()
        .iter()
        .map(|name| {
            let operation: Operation =
                serde_json::from_value(json!(name)).expect("protocol operation names deserialize");
            let (available, reason) = match operation {
                Operation::Ping
                | Operation::EngineInfo
                | Operation::DescribeExtent
                | Operation::ExtentContains
                | Operation::ExtentIntersects
                | Operation::DescribeCrs
                | Operation::DescribeZoomRange
                | Operation::TileFromLonLat
                | Operation::TileBounds
                | Operation::PlanTiles
                | Operation::ProjectInfo => (true, None),
                Operation::ApiDescribe
                | Operation::RenderMap
                | Operation::ExportFeatures
                | Operation::RenderProject => {
                    let route = if operation == Operation::RenderProject {
                        "render_map"
                    } else {
                        name
                    };
                    let supported = ready
                        && (operation == Operation::ApiDescribe
                            || manifest["operations"]
                                .as_array()
                                .is_some_and(|ops| ops.iter().any(|op| op == route)));
                    (
                        supported,
                        (!supported).then_some("QGIS backend does not provide this operation"),
                    )
                }
                Operation::ProjectLayers
                | Operation::AppInit
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
                | Operation::LayerFields => {
                    (false, Some("not implemented by this engine dispatcher"))
                }
            };
            json!({"name": name, "available": available, "reason": reason})
        })
        .collect();
    json!({
        "engine": ENGINE,
        "version": qgis_render::VERSION,
        "transport_version": TRANSPORT_VERSION,
        "backend": backend,
        "limits": {"max_zoom": qgis_render::MAX_ZOOM, "max_latitude": qgis_render::MAX_LATITUDE},
        "operations": operations,
    })
}
