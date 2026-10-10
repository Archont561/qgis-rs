//! Discovery through the engine's public reporting seam.
#[test]
fn discovery_distinguishes_known_operations_from_callable_ones() {
    let report = qgis_engine::discovery();
    assert_eq!(report["engine"], "qgis-engine");
    assert_eq!(report["transport_version"], 1);
    assert_eq!(report["limits"]["max_zoom"], 22);
    let operations = report["operations"].as_array().unwrap();
    let operation = |name: &str| operations.iter().find(|op| op["name"] == name).unwrap();
    assert_eq!(operation("plan_tiles")["available"], true);
    assert_eq!(operation("project_layers")["available"], false);
    assert_eq!(operation("app_init")["available"], false);
    assert!(operation("project_layers")["reason"].is_string());
    #[cfg(not(feature = "qgis"))]
    {
        assert_eq!(report["backend"]["available"], false);
        assert_eq!(report["backend"]["qgis_version"], serde_json::Value::Null);
        assert_eq!(operation("render_map")["available"], false);
    }
    assert_eq!(operations.len(), qgis_engine::Operation::all().len());
}

#[cfg(feature = "qgis")]
#[test]
fn native_discovery_reports_live_manager_support_not_just_a_build_flag() {
    let report = qgis_engine::discovery();
    assert_eq!(report["backend"]["available"], true, "{report}");
    assert!(report["backend"]["qgis_version"]
        .as_str()
        .unwrap()
        .starts_with("3."));
    for name in [
        "api_describe",
        "render_map",
        "export_features",
        "render_project",
    ] {
        let op = report["operations"]
            .as_array()
            .unwrap()
            .iter()
            .find(|op| op["name"] == name)
            .unwrap();
        assert_eq!(op["available"], true, "{name}: {report}");
    }
}
