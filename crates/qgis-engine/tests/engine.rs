//! The engine seen the way a binding sees it: text in, text out.
//!
//! These tests deliberately speak JSON rather than calling the typed helpers,
//! because JSON is what crosses the FFI boundary. A change that keeps the Rust
//! API working but renames a wire field has to fail here.

use qgis_engine::{invoke, Operation, TRANSPORT_VERSION};
use serde_json::{json, Value};

/// Send one request and return the parsed response.
fn send(operation: &str, payload: Value) -> Value {
    let request = json!({
        "transport_version": TRANSPORT_VERSION,
        "operation": operation,
        "payload": payload,
    });
    serde_json::from_str(&invoke(&request.to_string())).expect("the engine answers JSON")
}

/// The `result` of a request that must succeed.
fn ok(operation: &str, payload: Value) -> Value {
    let response = send(operation, payload);
    assert_eq!(
        response["ok"],
        json!(true),
        "{operation} failed: {response}"
    );
    assert_eq!(response["transport_version"], json!(TRANSPORT_VERSION));
    response["result"].clone()
}

/// The `result` of a request that must fail, checked for its kind.
fn err(operation: &str, payload: Value, kind: &str) -> Value {
    let response = send(operation, payload);
    assert_eq!(
        response["ok"],
        json!(false),
        "{operation} unexpectedly succeeded: {response}"
    );
    assert_eq!(response["result"]["kind"], json!(kind), "{response}");
    response["result"].clone()
}

#[test]
fn ping_echoes_the_payload_unchanged() {
    let result = ok("ping", json!({"nested": [1, "two", null]}));
    assert_eq!(result["engine"], json!("qgis-engine"));
    assert_eq!(result["echo"], json!({"nested": [1, "two", null]}));
}

#[test]
fn engine_info_advertises_the_operations_it_serves() {
    let result = ok("engine_info", Value::Null);
    assert_eq!(result["transport_version"], json!(TRANSPORT_VERSION));
    assert_eq!(result["max_zoom"], json!(22));
    assert!(result["version"].as_str().expect("a version").contains('.'));

    let operations = result["operations"].as_array().expect("a list");
    for name in ["ping", "plan_tiles", "render_project"] {
        assert!(
            operations.contains(&json!(name)),
            "{name} is served but not advertised"
        );
    }
    // Everything advertised must actually dispatch; `ping` with no payload is
    // rejected by nothing, so a bad name shows up as invalid_request.
    for name in operations {
        let response = send(name.as_str().expect("a string"), Value::Null);
        assert_ne!(
            response["result"]["kind"],
            json!("invalid_request"),
            "{name} is advertised but unknown to the dispatcher"
        );
    }
}

#[test]
fn an_extent_can_arrive_as_text_or_as_edges() {
    let from_text = ok("describe_extent", json!({"extent": "14, 50, 15, 51"}));
    let from_edges = ok(
        "describe_extent",
        json!({"extent": {"min_x": 14.0, "min_y": 50.0, "max_x": 15.0, "max_y": 51.0}}),
    );
    assert_eq!(from_text, from_edges);
    assert_eq!(from_text["width"], json!(1.0));
    assert_eq!(from_text["height"], json!(1.0));
    assert_eq!(from_text["is_valid"], json!(true));
    assert_eq!(from_text["extent"]["min_x"], json!(14.0));
}

#[test]
fn extent_predicates_answer_in_booleans() {
    let contains = ok(
        "extent_contains",
        json!({"extent": "14,50,15,51", "x": 14.5, "y": 50.5}),
    );
    assert_eq!(contains["contains"], json!(true));

    let intersects = ok(
        "extent_intersects",
        json!({"extent": "0,0,10,10", "other": "20,20,30,30"}),
    );
    assert_eq!(intersects["intersects"], json!(false));
}

#[test]
fn a_crs_reports_its_name_and_units() {
    let result = ok("describe_crs", json!({"text": " epsg:3857 "}));
    assert_eq!(result["auth_id"], json!("EPSG:3857"));
    assert_eq!(result["name"], json!("WGS 84 / Pseudo-Mercator"));
    assert_eq!(result["units"], json!("meters"));
    assert_eq!(result["is_geographic"], json!(false));

    // A well-formed code the built-in table does not know is described, not
    // rejected — the same rule qgis-render states.
    let unknown = ok("describe_crs", json!({"text": "EPSG:2154"}));
    assert_eq!(unknown["name"], Value::Null);
    assert_eq!(unknown["units"], json!("unknown"));
}

#[test]
fn a_zoom_range_arrives_as_a_number_a_string_or_a_pair() {
    for payload in [
        json!({"zooms": 12}),
        json!({"zooms": "12"}),
        json!({"zooms": {"min": 12, "max": 12}}),
    ] {
        let result = ok("describe_zoom_range", payload);
        assert_eq!(result["zooms"], json!({"min": 12, "max": 12}));
        assert_eq!(result["count"], json!(1));
    }
}

#[test]
fn tiles_round_trip_between_coordinates_and_bounds() {
    let located = ok(
        "tile_from_lon_lat",
        json!({"z": 10, "lon": 13.9, "lat": 51.1}),
    );
    assert_eq!(located["tile"], json!({"z": 10, "x": 551, "y": 342}));

    let bounds = ok(
        "tile_bounds",
        json!({"tile": {"z": 10, "x": 551, "y": 342}}),
    );
    assert_eq!(bounds["bounds"], located["bounds"]);
    assert_eq!(bounds["bounds"]["min_x"], json!(13.710_937_5));
}

#[test]
fn a_plan_counts_tiles_per_level_and_in_total() {
    let result = ok(
        "plan_tiles",
        json!({"bounds": "14,50,15,51", "zooms": "10-14"}),
    );
    assert_eq!(result["tile_count"], json!(4568));

    let levels = result["levels"].as_array().expect("one row per level");
    assert_eq!(levels.len(), 5);
    assert_eq!(
        levels[0],
        json!({"zoom": 10, "x_min": 551, "x_max": 554, "y_min": 342, "y_max": 347, "tile_count": 24})
    );
    assert!(result.get("tiles").is_none(), "enumeration is opt-in");
}

#[test]
fn enumerating_tiles_is_opt_in_and_matches_the_count() {
    let result = ok(
        "plan_tiles",
        json!({"bounds": "14,50,15,51", "zooms": 10, "include_tiles": true}),
    );
    let tiles = result["tiles"].as_array().expect("enumerated tiles");
    assert_eq!(
        tiles.len() as u64,
        result["tile_count"].as_u64().expect("a count")
    );
    assert_eq!(tiles[0], json!({"z": 10, "x": 551, "y": 342}));
}

#[test]
fn a_project_is_described_from_its_path() {
    let dir = std::env::temp_dir().join("qgis-engine-project-info");
    std::fs::create_dir_all(&dir).expect("create dir");
    let path = dir.join("map.qgs");
    std::fs::write(&path, b"<qgis></qgis>").expect("write project");

    let result = ok("project_info", json!({"path": path}));
    assert_eq!(result["format"], json!("qgs"));
    assert_eq!(result["size_bytes"], json!(13));
    assert!(
        result["note"].is_string(),
        "the missing fields explain themselves"
    );
    assert_eq!(result["crs"], Value::Null);
}

#[test]
fn work_that_needs_the_qgis_backend_says_so_in_a_kind() {
    let dir = std::env::temp_dir().join("qgis-engine-unimplemented");
    std::fs::create_dir_all(&dir).expect("create dir");
    let path = dir.join("map.qgs");
    std::fs::write(&path, b"<qgis></qgis>").expect("write project");

    let layers = err("project_layers", json!({"path": &path}), "unimplemented");
    assert!(layers["error"]
        .as_str()
        .expect("a message")
        .contains("QGIS backend"));

    err(
        "render_project",
        json!({"path": &path, "output": "out.png"}),
        "unimplemented",
    );
}

#[test]
fn every_rejection_carries_a_kind_a_client_can_branch_on() {
    err(
        "describe_extent",
        json!({"extent": "nonsense"}),
        "invalid_extent",
    );
    err(
        "describe_zoom_range",
        json!({"zooms": "14-10"}),
        "invalid_zoom_range",
    );
    err("describe_crs", json!({"text": "3857"}), "unknown_crs");
    err(
        "project_info",
        json!({"path": "/nope/missing.qgs"}),
        "project_not_found",
    );
    err(
        "render_project",
        json!({"path": "/nope/missing.qgs", "output": "out.bmp"}),
        "project_not_found",
    );
    // A payload of the wrong shape is reported before any domain rule runs.
    err("describe_extent", json!({"extent": 42}), "invalid_payload");
    err(
        "extent_contains",
        json!({"extent": "14,50,15,51"}),
        "invalid_payload",
    );
}

#[test]
fn a_request_that_is_not_an_envelope_is_rejected_as_one() {
    let response: Value = serde_json::from_str(&invoke("not json at all")).expect("still answers");
    assert_eq!(response["ok"], json!(false));
    assert_eq!(response["result"]["kind"], json!("invalid_request"));
    assert_eq!(response["transport_version"], json!(TRANSPORT_VERSION));
}

#[test]
fn a_future_transport_version_is_refused_rather_than_guessed() {
    let request = json!({"transport_version": 99, "operation": "ping"});
    let response: Value =
        serde_json::from_str(&invoke(&request.to_string())).expect("still answers");
    assert_eq!(response["result"]["kind"], json!("unsupported_transport"));
    assert_eq!(response["result"]["supported"], json!(TRANSPORT_VERSION));
    assert_eq!(response["result"]["received"], json!(99));
}

#[test]
fn the_typed_helper_and_the_text_path_agree() {
    let typed = qgis_engine::call(Operation::DescribeExtent, json!({"extent": "14,50,15,51"}));
    let text = send("describe_extent", json!({"extent": "14,50,15,51"}));
    assert_eq!(serde_json::to_value(&typed).expect("serialisable"), text);
}
