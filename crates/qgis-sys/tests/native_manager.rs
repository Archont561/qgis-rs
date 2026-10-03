#![cfg(feature = "qgis")]

use qgis_sys::native_manager_ffi as manager;
use serde_json::{json, Value};

fn response(request: Value) -> Value {
    serde_json::from_str(&manager::invoke(&request.to_string())).expect("manager returns JSON")
}

fn ok(operation: &str, payload: Value) -> Value {
    let answer = response(json!({
        "transport_version": 1,
        "operation": operation,
        "payload": payload,
    }));
    assert_eq!(answer["ok"], true, "manager rejected request: {answer}");
    assert_eq!(answer["transport_version"], 1);
    answer["result"].clone()
}

#[test]
fn manager_initializes_and_reports_engine_info() {
    let initialized = ok("app_init", Value::Null);
    assert_eq!(initialized["initialized"], true);

    let info = ok("engine_info", Value::Null);
    assert_eq!(info["transport_version"], 1);
    assert!(info["qgis_version"].as_str().unwrap().contains('.'));
    assert!(info["operations"]
        .as_array()
        .unwrap()
        .iter()
        .any(|operation| operation == "layer_new"));
}

#[test]
fn engine_info_exposes_the_complete_native_operation_catalogue() {
    let actual = ok("app_init", Value::Null)["initialized"];
    assert_eq!(actual, true);

    let mut operations: Vec<String> = ok("engine_info", Value::Null)["operations"]
        .as_array()
        .expect("operation catalogue")
        .iter()
        .map(|operation| operation.as_str().expect("operation name").to_string())
        .collect();
    operations.sort();

    let mut expected = vec![
        "app_init",
        "app_shutdown",
        "engine_info",
        "export_features",
        "layer_close",
        "layer_crs_authid",
        "layer_feature_count",
        "layer_features",
        "layer_fields",
        "layer_geometry_type_name",
        "layer_info",
        "layer_is_valid",
        "layer_name",
        "layer_new",
        "layer_open",
        "render_map",
    ];
    expected.sort();
    assert_eq!(operations, expected);
}

#[test]
fn manager_routes_vector_layer_operations_through_owned_ids() {
    ok("app_init", Value::Null);
    let path = format!("{}/tests/fixtures/points.gpkg", env!("CARGO_MANIFEST_DIR"));
    let created = ok(
        "layer_new",
        json!({"uri": path, "name": "points", "provider": "ogr"}),
    );
    let layer_id = created["layer_id"].as_u64().expect("integer layer id");
    assert_eq!(created["is_valid"], true);

    assert_eq!(
        ok("layer_is_valid", json!({"layer_id": layer_id}))["is_valid"],
        true
    );
    assert_eq!(
        ok("layer_name", json!({"layer_id": layer_id}))["name"],
        "points"
    );
    assert_eq!(
        ok("layer_feature_count", json!({"layer_id": layer_id}))["feature_count"],
        3
    );
    assert_eq!(
        ok("layer_crs_authid", json!({"layer_id": layer_id}))["auth_id"],
        "EPSG:4326"
    );
    assert!(
        ok("layer_geometry_type_name", json!({"layer_id": layer_id}))["name"]
            .as_str()
            .unwrap()
            .contains("Point")
    );

    let fields = ok("layer_fields", json!({"layer_id": layer_id}));
    assert_eq!(fields["fields"][0]["name"], "fid");
    assert_eq!(fields["fields"][0]["type"], "Integer64");
    assert_eq!(fields["fields"][1]["name"], "name");
    assert_eq!(fields["fields"][1]["type"], "String");
}

#[test]
fn manager_rejects_invalid_requests_and_ids_as_error_envelopes() {
    let malformed: Value = serde_json::from_str(&manager::invoke("not json")).unwrap();
    assert_eq!(malformed["ok"], false);
    assert_eq!(malformed["result"]["kind"], "invalid_request");

    ok("app_init", Value::Null);
    let invalid_id = response(json!({
        "transport_version": 1,
        "operation": "layer_name",
        "payload": {"layer_id": 999_999}
    }));
    assert_eq!(invalid_id["ok"], false);
    assert_eq!(invalid_id["result"]["kind"], "invalid_object_id");
}

#[test]
fn concurrent_callers_are_serialized_by_the_manager_owner() {
    ok("app_init", Value::Null);
    let workers = (0..4)
        .map(|_| {
            std::thread::spawn(|| {
                let info = ok("engine_info", Value::Null);
                assert_eq!(info["initialized"], true);
            })
        })
        .collect::<Vec<_>>();

    for worker in workers {
        worker.join().expect("manager caller should not panic");
    }
}

#[test]
fn transport_version_is_available_without_starting_qgis() {
    assert_eq!(manager::transport_version(), 1);
}

#[test]
fn manager_opens_reports_batches_and_closes_a_layer() {
    ok("app_init", Value::Null);
    let opened = ok(
        "layer_open",
        json!({
            "uri": format!("{}/tests/fixtures/points.gpkg", env!("CARGO_MANIFEST_DIR")),
            "provider": "ogr",
            "name": "points",
        }),
    );
    let layer_id = opened["layer_id"].as_u64().expect("integer layer id");
    assert_eq!(opened["is_valid"], true);
    assert_eq!(opened["name"], "points");

    let info = ok("layer_info", json!({"layer_id": layer_id}));
    assert_eq!(info["layer_id"], layer_id);
    assert_eq!(info["feature_count"], 3);
    assert_eq!(info["crs_authid"], "EPSG:4326");
    assert!(info["geometry_type_name"]
        .as_str()
        .unwrap()
        .contains("Point"));
    assert_eq!(
        info["fields"][0],
        json!({"name": "fid", "type": "Integer64", "precision": 0})
    );
    assert_eq!(
        info["fields"][1],
        json!({"name": "name", "type": "String", "precision": 0})
    );

    let page = ok(
        "layer_features",
        json!({"layer_id": layer_id, "offset": 0, "limit": 2}),
    );
    assert_eq!(page["layer_id"], layer_id);
    assert_eq!(page["offset"], 0);
    assert_eq!(page["limit"], 2);
    assert_eq!(page["total"], 3);
    assert_eq!(page["next_offset"], 2);
    assert_eq!(page["features"].as_array().unwrap().len(), 2);
    assert_eq!(
        page["features"][0],
        json!({
            "id": 1,
            "attributes": {"fid": 1, "name": "alpha"},
            "geometry_wkt": "Point (0 0)"
        })
    );
    assert_eq!(
        page["features"][1],
        json!({
            "id": 2,
            "attributes": {"fid": 2, "name": "beta"},
            "geometry_wkt": "Point (1 1)"
        })
    );

    let tail = ok(
        "layer_features",
        json!({"layer_id": layer_id, "offset": 2, "limit": 2}),
    );
    assert_eq!(tail["features"].as_array().unwrap().len(), 1);
    assert_eq!(tail["next_offset"], Value::Null);

    assert_eq!(
        ok("layer_close", json!({"layer_id": layer_id}))["closed"],
        true
    );
    let closed = response(json!({
        "transport_version": 1,
        "operation": "layer_info",
        "payload": {"layer_id": layer_id}
    }));
    assert_eq!(closed["ok"], false);
    assert_eq!(closed["result"]["kind"], "invalid_object_id");

    let closed_twice = response(json!({
        "transport_version": 1,
        "operation": "layer_close",
        "payload": {"layer_id": layer_id}
    }));
    assert_eq!(closed_twice["ok"], false);
    assert_eq!(closed_twice["result"]["kind"], "invalid_object_id");
}


#[test]
fn phase_four_operations_render_and_export_real_qgis_artifacts() {
    ok("app_init", Value::Null);
    let project = format!("{}/tests/fixtures/points.qgs", env!("CARGO_MANIFEST_DIR"));
    let output_dir = std::env::temp_dir().join(format!(
        "qgis-rs-phase-four-{}",
        std::process::id()
    ));
    std::fs::create_dir_all(&output_dir).expect("create output directory");
    let image_path = output_dir.join("points.png");
    let geojson_path = output_dir.join("points.geojson");

    let rendered = ok(
        "render_map",
        json!({
            "project": project,
            "output": image_path,
            "width": 64,
            "height": 48,
            "dpi": 96,
            "crs": "EPSG:4326",
            "extent": "-1,-1,3,3"
        }),
    );
    assert_eq!(rendered["format"], "png");
    assert_eq!(rendered["width"], 64);
    assert_eq!(rendered["height"], 48);
    assert!(rendered["bytes"].as_u64().unwrap() > 0);
    assert!(image_path.is_file());

    let exported = ok(
        "export_features",
        json!({
            "project": format!("{}/tests/fixtures/points.qgs", env!("CARGO_MANIFEST_DIR")),
            "layer": "points",
            "output": geojson_path,
            "bbox": "-1,-1,3,3",
            "fields": ["name"]
        }),
    );
    assert_eq!(exported["format"], "geojson");
    assert_eq!(exported["layer"], "points");
    assert_eq!(exported["feature_count"], 3);
    assert!(exported["bytes"].as_u64().unwrap() > 0);
    let collection: Value = serde_json::from_str(
        &std::fs::read_to_string(&geojson_path).expect("read GeoJSON artifact"),
    )
    .expect("parse GeoJSON artifact");
    assert_eq!(collection["type"], "FeatureCollection");
    assert_eq!(collection["features"].as_array().unwrap().len(), 3);

    let _ = std::fs::remove_dir_all(output_dir);
}

#[test]
fn phase_four_operations_are_native_and_return_path_errors_not_placeholders() {
    ok("app_init", Value::Null);
    let info = ok("engine_info", Value::Null);
    for operation in ["render_map", "export_features"] {
        assert!(info["operations"]
            .as_array()
            .expect("operations")
            .iter()
            .any(|advertised| advertised == operation));
    }

    let render = response(json!({
        "transport_version": 1,
        "operation": "render_map",
        "payload": {"project": "/missing/project.qgs", "output": "/tmp/map.png"}
    }));
    assert_eq!(render["ok"], false);
    assert_eq!(render["result"]["kind"], "qgis");

    let export = response(json!({
        "transport_version": 1,
        "operation": "export_features",
        "payload": {
            "project": "/missing/project.qgs",
            "layer": "points",
            "output": "/tmp/points.geojson"
        }
    }));
    assert_eq!(export["ok"], false);
    assert_eq!(export["result"]["kind"], "qgis");
    assert_ne!(render["result"]["kind"], "unimplemented");
    assert_ne!(export["result"]["kind"], "unimplemented");
}
