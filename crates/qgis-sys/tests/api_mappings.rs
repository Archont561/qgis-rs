#![cfg(feature = "qgis")]

use qgis_sys::native_manager_ffi as manager;
use serde_json::{json, Value};
use std::path::PathBuf;

/// The native manager's public JSON entry point used by the mapping contract tests.
#[derive(Clone, Copy)]
struct NativeManager;

impl NativeManager {
    fn response(&self, operation: &str, payload: Value) -> Value {
        serde_json::from_str(&manager::invoke(
            &json!({
                "transport_version": 1,
                "operation": operation,
                "payload": payload,
            })
            .to_string(),
        ))
        .expect("native manager returns a JSON envelope")
    }

    fn ok(&self, operation: &str, payload: Value) -> Value {
        let response = self.response(operation, payload);
        assert_eq!(response["ok"], true, "manager rejected request: {response}");
        assert_eq!(response["transport_version"], 1);
        response["result"].clone()
    }

    fn error(&self, operation: &str, payload: Value) -> Value {
        let response = self.response(operation, payload);
        assert_eq!(
            response["ok"], false,
            "manager unexpectedly accepted request"
        );
        assert_eq!(response["transport_version"], 1);
        response["result"].clone()
    }

    fn initialize(&self) {
        assert_eq!(self.ok("app_init", Value::Null)["initialized"], true);
    }

    fn open_points(&self) -> u64 {
        let opened = self.ok(
            "layer_open",
            json!({
                "uri": points_path(),
                "provider": "ogr",
                "name": "points",
            }),
        );
        assert_eq!(opened["is_valid"], true);
        opened["layer_id"].as_u64().expect("manager-owned layer ID")
    }

    fn close_layer(&self, layer_id: u64) {
        assert_eq!(
            self.ok("layer_close", json!({"layer_id": layer_id}))["closed"],
            true
        );
    }
}

fn points_path() -> String {
    format!("{}/tests/fixtures/points.gpkg", env!("CARGO_MANIFEST_DIR"))
}

fn project_path() -> String {
    format!("{}/tests/fixtures/points.qgs", env!("CARGO_MANIFEST_DIR"))
}

fn output_dir(test_name: &str) -> PathBuf {
    let directory =
        std::env::temp_dir().join(format!("qgis-rs-task30-{test_name}-{}", std::process::id()));
    if directory.exists() {
        std::fs::remove_dir_all(&directory).expect("remove stale test output directory");
    }
    std::fs::create_dir_all(&directory).expect("create test output directory");
    directory
}

#[test]
fn ownership_maps_qgis_objects_to_distinct_manager_owned_wire_ids() {
    let native_manager = NativeManager;
    native_manager.initialize();

    let first_id = native_manager.open_points();
    let second_id = native_manager.open_points();
    assert_ne!(first_id, second_id);
    assert_eq!(
        native_manager.ok("layer_name", json!({"layer_id": first_id}))["name"],
        "points"
    );

    native_manager.close_layer(first_id);
    native_manager.close_layer(second_id);
}

#[test]
fn invalidation_rejects_layer_ids_after_close_without_reaching_qgis() {
    let native_manager = NativeManager;
    native_manager.initialize();
    let layer_id = native_manager.open_points();
    native_manager.close_layer(layer_id);

    let stale_info = native_manager.error("layer_info", json!({"layer_id": layer_id}));
    assert_eq!(stale_info["kind"], "invalid_object_id");

    let duplicate_close = native_manager.error("layer_close", json!({"layer_id": layer_id}));
    assert_eq!(duplicate_close["kind"], "invalid_object_id");
}

#[test]
fn overload_uses_request_bearing_get_features_for_expression_filters() {
    let native_manager = NativeManager;
    native_manager.initialize();
    let directory = output_dir("request-overload");
    let output = directory.join("filtered.geojson");

    let exported = native_manager.ok(
        "export_features",
        json!({
            "project": project_path(),
            "layer": "points",
            "output": output,
            "filter": "\"name\" = 'beta'",
            "fields": ["name"],
        }),
    );

    assert_eq!(exported["feature_count"], 1);
    let collection: Value = serde_json::from_slice(
        &std::fs::read(directory.join("filtered.geojson")).expect("read filtered GeoJSON"),
    )
    .expect("parse filtered GeoJSON");
    assert_eq!(collection["features"].as_array().unwrap().len(), 1);
    assert_eq!(
        collection["features"][0]["properties"],
        json!({"name": "beta"})
    );

    std::fs::remove_dir_all(directory).expect("remove filtered export directory");
}

#[test]
fn enum_mappings_expose_stable_names_instead_of_qgis_numeric_values() {
    let native_manager = NativeManager;
    native_manager.initialize();
    let layer_id = native_manager.open_points();

    let info = native_manager.ok("layer_info", json!({"layer_id": layer_id}));
    assert_eq!(info["geometry_type_name"], "Point");
    assert_eq!(info["fields"][0]["type"], "Integer64");
    assert_eq!(info["fields"][1]["type"], "String");

    native_manager.close_layer(layer_id);
}

#[test]
fn variant_mappings_preserve_integer_and_string_json_scalars() {
    let native_manager = NativeManager;
    native_manager.initialize();
    let layer_id = native_manager.open_points();

    let page = native_manager.ok(
        "layer_features",
        json!({"layer_id": layer_id, "offset": 0, "limit": 1}),
    );
    let attributes = &page["features"][0]["attributes"];
    assert!(attributes["fid"].is_number());
    assert_eq!(attributes["fid"].as_u64(), Some(1));
    assert!(attributes["name"].is_string());
    assert_eq!(attributes["name"].as_str(), Some("alpha"));

    native_manager.close_layer(layer_id);
}

#[test]
fn binary_artifacts_stay_at_paths_and_return_only_format_and_byte_metadata() {
    let native_manager = NativeManager;
    native_manager.initialize();
    let directory = output_dir("binary-artifact");
    let image_path = directory.join("points.png");
    let export_path = directory.join("points.geojson");

    let rendered = native_manager.ok(
        "render_map",
        json!({
            "project": project_path(),
            "output": image_path,
            "width": 64,
            "height": 48,
            "dpi": 96,
            "crs": "EPSG:4326",
            "extent": "-1,-1,3,3",
        }),
    );
    assert_eq!(rendered["format"], "png");
    assert_eq!(rendered["path"], image_path.to_string_lossy().as_ref());
    assert_eq!(rendered["width"], 64);
    assert_eq!(rendered["height"], 48);
    assert_eq!(
        rendered["bytes"].as_u64(),
        Some(
            std::fs::metadata(&image_path)
                .expect("image artifact exists")
                .len()
        )
    );
    assert!(rendered.get("data").is_none());
    let image = std::fs::read(&image_path).expect("read rendered image");
    assert!(image.starts_with(b"\x89PNG\r\n\x1a\n"));

    let exported = native_manager.ok(
        "export_features",
        json!({
            "project": project_path(),
            "layer": "points",
            "output": export_path,
            "fields": ["name"],
        }),
    );
    assert_eq!(exported["format"], "geojson");
    assert_eq!(exported["path"], export_path.to_string_lossy().as_ref());
    assert_eq!(
        exported["bytes"].as_u64(),
        Some(
            std::fs::metadata(&export_path)
                .expect("feature artifact exists")
                .len()
        )
    );
    assert!(exported.get("data").is_none());

    std::fs::remove_dir_all(directory).expect("remove artifact directory");
}

#[test]
fn paging_resumes_at_next_offset_without_losing_or_repeating_features() {
    let native_manager = NativeManager;
    native_manager.initialize();
    let layer_id = native_manager.open_points();

    let first_page = native_manager.ok(
        "layer_features",
        json!({"layer_id": layer_id, "offset": 0, "limit": 2}),
    );
    assert_eq!(first_page["total"], 3);
    assert_eq!(first_page["offset"], 0);
    assert_eq!(first_page["limit"], 2);
    assert_eq!(first_page["features"].as_array().unwrap().len(), 2);
    let next_offset = first_page["next_offset"]
        .as_u64()
        .expect("more features have a next offset");
    assert_eq!(next_offset, 2);

    let last_page = native_manager.ok(
        "layer_features",
        json!({"layer_id": layer_id, "offset": next_offset, "limit": 2}),
    );
    assert_eq!(last_page["total"], 3);
    assert_eq!(last_page["offset"], next_offset);
    assert_eq!(last_page["features"].as_array().unwrap().len(), 1);
    assert!(last_page["next_offset"].is_null());

    let feature_ids = first_page["features"]
        .as_array()
        .unwrap()
        .iter()
        .chain(last_page["features"].as_array().unwrap())
        .map(|feature| feature["id"].as_i64().expect("feature ID"))
        .collect::<Vec<_>>();
    assert_eq!(feature_ids, [1, 2, 3]);

    native_manager.close_layer(layer_id);
}
