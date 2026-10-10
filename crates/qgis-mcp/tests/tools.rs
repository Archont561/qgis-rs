//! The MCP surface as a client meets it: which tools are advertised, which
//! native backend is loaded, and what the live tools answer.
//!
//! The tool list is a contract — an agent that discovered `plan_tiles`
//! yesterday must still find it today — so it is asserted by name here.

use std::ops::Deref;
use std::path::{Path, PathBuf};

use qgis_mcp::*;
use qgis_render::{Extent, ZoomRange};
use rmcp::handler::server::wrapper::Parameters;
use rstest::{fixture, rstest};

/// A project file on disk that deletes itself afterwards.
///
/// Derefs to [`Path`], so it is used exactly where the previous
/// `project_file(name) -> PathBuf` helper was.
struct ProjectFile {
    dir: PathBuf,
    path: PathBuf,
}

impl ProjectFile {
    fn as_path(&self) -> &Path {
        &self.path
    }

    /// The path as the tool parameters want it: an owned `String`.
    fn as_str(&self) -> String {
        self.path.to_str().expect("utf-8").to_owned()
    }
}

impl Deref for ProjectFile {
    type Target = Path;

    fn deref(&self) -> &Path {
        &self.path
    }
}

impl Drop for ProjectFile {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.dir).ok();
    }
}

/// A minimal project. Tests that care about the file name override it with
/// `#[with("render.qgs")]`; the rest take the default.
#[fixture]
fn project_file(#[default("map.qgs")] name: &str) -> ProjectFile {
    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .expect("system clock is after the epoch")
        .as_nanos();
    let dir = std::env::temp_dir().join(format!("qgis-mcp-tests-{unique}"));
    std::fs::create_dir_all(&dir).expect("create dir");
    let path = dir.join(name);
    std::fs::write(&path, b"<qgis></qgis>").expect("write");
    ProjectFile { dir, path }
}

/// The MCP server under test.
#[fixture]
fn server() -> QgisMcpServer {
    QgisMcpServer::new()
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
fn capabilities_reports_the_loaded_backend() {
    let report = QgisMcpServer::capabilities_report();
    assert_eq!(report.server, "qgis-cli");
    assert_eq!(report.tools.len(), 6);
    assert!(!report.backend.is_empty());
    assert_eq!(
        report
            .tools
            .iter()
            .filter(|tool| tool.name == "render_map")
            .count(),
        1
    );
    let render = report
        .tools
        .iter()
        .find(|tool| tool.name == "render_map")
        .unwrap();
    let export = report
        .tools
        .iter()
        .find(|tool| tool.name == "export_features")
        .unwrap();
    assert_eq!(render.available, export.available);
    assert_eq!(render.available, cfg!(feature = "qgis"));
    #[cfg(feature = "qgis")]
    {
        assert!(render.available);
        assert!(report.qgis_version.is_some());
        assert_ne!(report.backend, "unavailable");
    }
    #[cfg(not(feature = "qgis"))]
    {
        assert!(!render.available);
        assert_eq!(report.qgis_version, None);
        assert_eq!(report.backend, "unavailable");
    }
    let json = serde_json::to_string(&report).expect("serialisable");
    assert!(json.contains("backend"));
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
    assert_eq!(plan.tile_count, 4568);
    assert_eq!(plan.levels.len(), 5);
    assert_eq!(plan.levels[0].tile_count, 24);
    assert_eq!(plan.zooms, ZoomRange::new(10, 14).expect("valid"));
    assert_eq!(plan.bounds, Extent::parse("14,50,15,51").expect("valid"));

    let error = QgisMcpServer::plan_tiles_report("14,50,15", "10-14").expect_err("bad bounds");
    assert!(format!("{error:?}").contains("extent"));
    assert!(QgisMcpServer::plan_tiles_report("14,50,15,51", "99").is_err());
}

/// The MCP answer is the shared report, not a second spelling of it.
///
/// MCP once carried its own shape: `total_tiles` where the engine says
/// `tile_count`, and a per-level `tiles` *count* where the engine's top-level
/// `tiles` is the *enumerated array* — the same word meaning two things across
/// one boundary. This pins the reconciliation.
#[test]
fn plan_tiles_serialises_under_the_shared_report_keys() {
    let plan = QgisMcpServer::plan_tiles_report("14,50,15,51", "10-14").expect("valid");

    let value = serde_json::to_value(&plan).expect("serialises");

    let mut keys: Vec<&String> = value.as_object().expect("object").keys().collect();
    keys.sort();
    assert_eq!(keys, ["bounds", "levels", "tile_count", "zooms"]);

    let mut level_keys: Vec<&String> = value["levels"][0]
        .as_object()
        .expect("object")
        .keys()
        .collect();
    level_keys.sort();
    assert_eq!(
        level_keys,
        ["tile_count", "x_max", "x_min", "y_max", "y_min", "zoom"]
    );
    assert_eq!(value["tile_count"], serde_json::json!(4568));
}

#[rstest]
fn project_info_describes_a_project_without_qgis(
    #[with("capabilities.qgs")] project_file: ProjectFile,
) {
    let info = QgisMcpServer::project_info_report(&project_file.as_str()).expect("project");
    assert_eq!(info.format, "qgs");
    assert!(info.size_bytes > 0);
    assert_eq!(info.crs, None);
    assert_eq!(info.layer_count, None);
    assert!(info.note.expect("note").contains("QGIS backend"));

    let error = QgisMcpServer::project_info_report("/nope/missing.qgs").expect_err("missing");
    assert!(format!("{error:?}").contains("not found"));
}

#[rstest]
fn render_requests_are_validated_before_they_reach_qgis(
    #[with("render.qgs")] project_file: ProjectFile,
) {
    let project = project_file.as_str();

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
    assert_eq!(opened.path(), project_file.as_path());
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

#[rstest]
fn render_and_export_handlers_cross_the_manager_boundary(
    #[with("native-dispatch.qgs")] project_file: ProjectFile,
    server: QgisMcpServer,
) {
    let project = project_file.as_str();

    let render_error = server
        .render_map(Parameters(RenderMapParams {
            project: project.clone(),
            output: project_file.with_extension("png").display().to_string(),
            extent: None,
            width: Some(32),
            height: Some(32),
            crs: None,
            dpi: None,
            layers: None,
            layout: None,
        }))
        .expect_err("the deliberately empty project cannot render");
    assert!(!format!("{render_error:?}")
        .to_ascii_lowercase()
        .contains("unimplemented"));

    let export_error = server
        .export_features(Parameters(ExportFeaturesParams {
            project,
            layer: "points".to_string(),
            output: Some(project_file.with_extension("geojson").display().to_string()),
            filter: None,
            bbox: None,
            fields: None,
        }))
        .expect_err("the deliberately empty project cannot export");
    assert!(!format!("{export_error:?}")
        .to_ascii_lowercase()
        .contains("unimplemented"));
}

#[rstest]
fn export_requests_default_to_the_whole_world(#[with("export.qgs")] project_file: ProjectFile) {
    let project = project_file.as_str();

    let (opened, bbox) = QgisMcpServer::export_request(&ExportFeaturesParams {
        project,
        layer: "buildings".to_string(),
        output: None,
        filter: None,
        bbox: None,
        fields: None,
    })
    .expect("valid request");
    assert_eq!(opened.path(), project_file.as_path());
    assert_eq!(bbox, Extent::new(-180.0, -90.0, 180.0, 90.0));

    let empty_layer = ExportFeaturesParams {
        project: project_file.as_str(),
        layer: "  ".to_string(),
        output: None,
        filter: None,
        bbox: Some("14,50,15,51".to_string()),
        fields: None,
    };
    assert!(QgisMcpServer::export_request(&empty_layer).is_err());
}

#[rstest]
fn tool_results_are_pretty_json(server: QgisMcpServer) {
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

#[rstest]
fn the_capabilities_tool_speaks_json(server: QgisMcpServer) {
    let text = server.capabilities().expect("text result");
    let parsed: serde_json::Value = serde_json::from_str(&text).expect("json");
    assert_eq!(parsed["server"], "qgis-cli");
    assert_eq!(parsed["tools"].as_array().expect("tools").len(), 6);
}
