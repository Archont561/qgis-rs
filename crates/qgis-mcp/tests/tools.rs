//! The MCP surface as a client meets it: which tools are advertised, which of
//! them admit to needing the QGIS backend, and what the live ones answer.
//!
//! The tool list is a contract — an agent that discovered `plan_tiles`
//! yesterday must still find it today — so it is asserted by name here.

use qgis_mcp::*;
use qgis_render::Extent;
use rmcp::handler::server::wrapper::Parameters;

fn project_file(name: &str) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join("qgis-mcp-tests");
    std::fs::create_dir_all(&dir).expect("create dir");
    let path = dir.join(name);
    std::fs::write(&path, b"<qgis></qgis>").expect("write");
    path
}

#[test]
fn advertises_exactly_the_expected_tools() {
    let mut names: Vec<String> = QgisMcpServer::tools()
        .list_all()
        .into_iter()
        .map(|tool| tool.name.to_string())
        .collect();
    names.sort();
    assert_eq!(
        names,
        [
            "capabilities",
            "crs_info",
            "export_features",
            "plan_tiles",
            "project_info",
            "render_map",
        ]
    );
}

#[test]
fn every_tool_has_a_description() {
    for tool in QgisMcpServer::tools().list_all() {
        let description = tool.description.expect("description present");
        assert!(description.len() > 20, "{}: {}", tool.name, description);
    }
}

#[test]
fn capabilities_flags_the_tools_that_need_qgis() {
    let report = QgisMcpServer::capabilities_report();
    assert_eq!(report.server, "qgis-cli");
    assert_eq!(report.tools.len(), 6);
    let mut needs_qgis: Vec<&str> = report
        .tools
        .iter()
        .filter(|tool| tool.needs_qgis_backend)
        .map(|tool| tool.name.as_str())
        .collect();
    needs_qgis.sort_unstable();
    assert_eq!(needs_qgis, ["export_features", "render_map"]);
    let json = serde_json::to_string(&report).expect("serialisable");
    assert!(json.contains("needs_qgis_backend"));
}

#[test]
fn crs_info_knows_web_mercator() {
    let crs = QgisMcpServer::crs_info_report("epsg:3857").expect("known code");
    assert_eq!(
        crs,
        CrsReport {
            auth_id: "EPSG:3857".to_string(),
            name: Some("WGS 84 / Pseudo-Mercator".to_string()),
            units: "meters".to_string(),
            geographic: false,
        }
    );
    assert!(QgisMcpServer::crs_info_report("not a crs").is_err());
}

#[test]
fn plan_tiles_counts_the_documented_pyramid() {
    let plan = QgisMcpServer::plan_tiles_report("14,50,15,51", "10-14").expect("valid");
    assert_eq!(plan.total_tiles, 4568);
    assert_eq!(plan.levels.len(), 5);
    assert_eq!(plan.levels[0].tiles, 24);
    assert_eq!(plan.zoom, "10-14");

    let error = QgisMcpServer::plan_tiles_report("14,50,15", "10-14").expect_err("bad bounds");
    assert!(format!("{error:?}").contains("extent"));
    assert!(QgisMcpServer::plan_tiles_report("14,50,15,51", "99").is_err());
}

#[test]
fn project_info_describes_a_project_without_qgis() {
    let path = project_file("capabilities.qgs");
    let info = QgisMcpServer::project_info_report(path.to_str().expect("utf-8")).expect("project");
    assert_eq!(info.format, "qgs");
    assert!(info.size_bytes > 0);
    assert_eq!(info.crs, None);
    assert_eq!(info.layer_count, None);
    assert!(info.note.expect("note").contains("QGIS backend"));

    let error = QgisMcpServer::project_info_report("/nope/missing.qgs").expect_err("missing");
    assert!(format!("{error:?}").contains("not found"));
}

#[test]
fn render_requests_are_validated_before_they_are_refused() {
    let path = project_file("render.qgs");
    let project = path.to_str().expect("utf-8").to_string();

    let good = RenderMapParams {
        project: project.clone(),
        output: "out.png".to_string(),
        extent: Some("14,50,15,51".to_string()),
        width: Some(2048),
        height: None,
        crs: Some("EPSG:3857".to_string()),
        dpi: Some(300.0),
        layers: Some("buildings, roads".to_string()),
        layout: None,
    };
    let (opened, settings) = QgisMcpServer::render_settings(&good).expect("valid request");
    assert_eq!(opened.path(), path.as_path());
    assert_eq!(settings.width, 2048);
    assert_eq!(settings.height, 768);
    assert_eq!(settings.dpi, 300.0);
    assert_eq!(settings.layers, vec!["buildings", "roads"]);

    let bad_extent = RenderMapParams {
        extent: Some("14,50,15".to_string()),
        ..good.clone()
    };
    assert!(QgisMcpServer::render_settings(&bad_extent).is_err());

    let bad_crs = RenderMapParams {
        crs: Some("nope".to_string()),
        ..good.clone()
    };
    assert!(QgisMcpServer::render_settings(&bad_crs).is_err());

    let bad_output = RenderMapParams {
        output: "out.bmp".to_string(),
        ..good.clone()
    };
    assert!(QgisMcpServer::render_settings(&bad_output).is_err());

    let missing = RenderMapParams {
        project: "/nope/missing.qgs".to_string(),
        ..good
    };
    assert!(QgisMcpServer::render_settings(&missing).is_err());
}

#[test]
fn export_requests_default_to_the_whole_world() {
    let path = project_file("export.qgs");
    let project = path.to_str().expect("utf-8").to_string();

    let (opened, bbox) = QgisMcpServer::export_request(&ExportFeaturesParams {
        project,
        layer: "buildings".to_string(),
        output: None,
        filter: None,
        bbox: None,
        fields: None,
    })
    .expect("valid request");
    assert_eq!(opened.path(), path.as_path());
    assert_eq!(bbox, Extent::new(-180.0, -90.0, 180.0, 90.0));

    let empty_layer = ExportFeaturesParams {
        project: path.to_str().expect("utf-8").to_string(),
        layer: "  ".to_string(),
        output: None,
        filter: None,
        bbox: Some("14,50,15,51".to_string()),
        fields: None,
    };
    assert!(QgisMcpServer::export_request(&empty_layer).is_err());
}

#[test]
fn tool_results_are_pretty_json() {
    let server = QgisMcpServer::new();
    let text = server
        .crs_info(Parameters(CrsInfoParams {
            auth_id: "EPSG:4326".to_string(),
        }))
        .expect("text result");
    let parsed: serde_json::Value = serde_json::from_str(&text).expect("json");
    assert_eq!(parsed["auth_id"], "EPSG:4326");
    assert_eq!(parsed["units"], "degrees");
    assert_eq!(parsed["geographic"], true);
}

#[test]
fn the_capabilities_tool_speaks_json() {
    let server = QgisMcpServer::new();
    let text = server.capabilities().expect("text result");
    let parsed: serde_json::Value = serde_json::from_str(&text).expect("json");
    assert_eq!(parsed["server"], "qgis-cli");
    assert_eq!(parsed["tools"].as_array().expect("tools").len(), 6);
}
