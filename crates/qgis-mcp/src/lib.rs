//! Model Context Protocol server for the qgis-rs engine.
//!
//! `qgis-mcp` turns the [`qgis_render`] API into MCP tools so that any MCP
//! client — Claude Desktop, Claude Code, Cursor, the MCP inspector — can drive
//! qgis-rs over stdio. It is a library: the `qgis-cli mcp` subcommand starts
//! it, and it can equally be embedded in another binary.
//!
//! ```no_run
//! # async fn run() -> anyhow::Result<()> {
//! // Called by `qgis-cli mcp`. Needs a Tokio runtime.
//! qgis_mcp::QgisMcpServer::new().serve_stdio().await
//! # }
//! ```
//!
//! Tools that only need geometry (`crs_info`, `plan_tiles`, `project_info`)
//! answer for real; the ones that need `libqgis_core` (`render_map`,
//! `export_features`) report that they are not wired up yet instead of
//! pretending. `capabilities` lists both, so a client can tell them apart.
//!
//! The `_report` helpers are the pure half of each tool: they take plain
//! arguments and return typed values, which is what the tests exercise.

use qgis_render::{Crs, Error as RenderError, Extent, Project, RenderSettings, TilePlan, ZoomRange};
use rmcp::{
    ErrorData, ServiceExt, handler::server::wrapper::Parameters, tool, tool_handler, tool_router,
    transport::stdio,
};

/// The implementation name reported during the MCP handshake.
pub const SERVER_NAME: &str = "qgis-cli";

/// Tools that cannot answer until `qgis-render` gains a QGIS backend.
const NEEDS_QGIS: &[&str] = &["render_map", "export_features"];

// ── tool arguments ────────────────────────────────────────────────────────────

/// Arguments for `crs_info`.
#[derive(Debug, Clone, serde::Deserialize, schemars::JsonSchema)]
pub struct CrsInfoParams {
    #[schemars(description = "Authority code of the CRS, e.g. \"EPSG:3857\".")]
    pub auth_id: String,
}

/// Arguments for `plan_tiles`.
#[derive(Debug, Clone, serde::Deserialize, schemars::JsonSchema)]
pub struct PlanTilesParams {
    #[schemars(
        description = "Area to cover in EPSG:4326, as \"minx,miny,maxx,maxy\", e.g. \"14,50,15,51\"."
    )]
    pub bounds: String,
    #[schemars(description = "Zoom levels, as a single level (\"12\") or a range (\"10-14\").")]
    pub zoom: String,
}

/// Arguments for `project_info`.
#[derive(Debug, Clone, serde::Deserialize, schemars::JsonSchema)]
pub struct ProjectInfoParams {
    #[schemars(description = "Path to a .qgs or .qgz project file.")]
    pub project: String,
}

/// Arguments for `render_map`.
#[derive(Debug, Clone, serde::Deserialize, schemars::JsonSchema)]
pub struct RenderMapParams {
    #[schemars(description = "Path to a .qgs or .qgz project file.")]
    pub project: String,
    #[schemars(description = "Where to write the image; the extension picks the format (.png, .jpg, .webp, .svg, .pdf).")]
    pub output: String,
    #[schemars(description = "Area to render in EPSG:4326, as \"minx,miny,maxx,maxy\". Defaults to the full extent.")]
    pub extent: Option<String>,
    #[schemars(description = "Image width in pixels. Defaults to 1024.")]
    pub width: Option<u32>,
    #[schemars(description = "Image height in pixels. Defaults to 768.")]
    pub height: Option<u32>,
    #[schemars(description = "CRS to render in, e.g. \"EPSG:3857\". Defaults to the project CRS.")]
    pub crs: Option<String>,
    #[schemars(description = "Resolution in dots per inch. Defaults to 96.")]
    pub dpi: Option<f64>,
    #[schemars(description = "Comma-separated layer names to draw. Defaults to every layer.")]
    pub layers: Option<String>,
    #[schemars(description = "Name of a print layout to render instead of the map canvas.")]
    pub layout: Option<String>,
}

/// Arguments for `export_features`.
#[derive(Debug, Clone, serde::Deserialize, schemars::JsonSchema)]
pub struct ExportFeaturesParams {
    #[schemars(description = "Path to a .qgs or .qgz project file.")]
    pub project: String,
    #[schemars(description = "Name of the layer to export.")]
    pub layer: String,
    #[schemars(description = "Where to write the output. Defaults to <layer>.geojson.")]
    pub output: Option<String>,
    #[schemars(description = "QGIS expression used to filter features.")]
    pub filter: Option<String>,
    #[schemars(description = "Bounding box in EPSG:4326, as \"minx,miny,maxx,maxy\".")]
    pub bbox: Option<String>,
    #[schemars(description = "Comma-separated attribute names to keep. Defaults to all of them.")]
    pub fields: Option<String>,
}

// ── tool results ──────────────────────────────────────────────────────────────

/// What `crs_info` returns.
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct CrsReport {
    /// Authority code, uppercased.
    pub auth_id: String,
    /// Human-readable name, when qgis-rs knows the code.
    pub name: Option<String>,
    /// `degrees`, `meters` or `unknown`.
    pub units: String,
    /// Whether the CRS is geographic.
    pub geographic: bool,
}

/// One zoom level of a tile plan.
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct ZoomLevelReport {
    /// The zoom level.
    pub zoom: u32,
    /// First column.
    pub x_min: u32,
    /// Last column.
    pub x_max: u32,
    /// First row.
    pub y_min: u32,
    /// Last row.
    pub y_max: u32,
    /// Tiles at this level.
    pub tiles: u64,
}

/// What `plan_tiles` returns.
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct TilePlanReport {
    /// The requested bounds, echoed back.
    pub bounds: String,
    /// The requested zoom range, echoed back.
    pub zoom: String,
    /// Tiles across every zoom level.
    pub total_tiles: u64,
    /// One entry per zoom level.
    pub levels: Vec<ZoomLevelReport>,
}

/// What `project_info` returns.
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct ProjectReport {
    /// The path that was inspected.
    pub path: String,
    /// `qgs` or `qgz`.
    pub format: String,
    /// Size on disk, in bytes.
    pub size_bytes: u64,
    /// Project CRS, when the backend can read it.
    pub crs: Option<String>,
    /// Layer count, when the backend can read it.
    pub layer_count: Option<usize>,
    /// Why some fields are missing.
    pub note: Option<String>,
}

/// One row of the `capabilities` report.
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct ToolReport {
    /// The MCP tool name.
    pub name: String,
    /// Its description.
    pub description: String,
    /// Whether it needs the QGIS backend.
    pub needs_qgis_backend: bool,
}

/// What `capabilities` returns.
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct CapabilitiesReport {
    /// The MCP implementation name.
    pub server: String,
    /// The qgis-rs version this server was built from.
    pub version: String,
    /// Every tool this server advertises.
    pub tools: Vec<ToolReport>,
    /// How to interpret the report.
    pub note: String,
}

/// The MCP server. Stateless: every tool call is answered on its own.
#[derive(Debug, Clone, Copy, Default)]
pub struct QgisMcpServer;

impl QgisMcpServer {
    /// Build a server.
    #[must_use]
    pub const fn new() -> Self {
        Self
    }

    /// Serve the MCP protocol over stdin/stdout until the client disconnects.
    ///
    /// Call this from inside a Tokio runtime, and keep stdout to yourself —
    /// the protocol owns it.
    ///
    /// # Errors
    ///
    /// Propagates transport and session failures from `rmcp`.
    pub async fn serve_stdio(self) -> anyhow::Result<()> {
        let service = self
            .serve(stdio())
            .await
            .map_err(|error| anyhow::anyhow!("could not start the MCP transport: {error:?}"))?;
        service
            .waiting()
            .await
            .map_err(|error| anyhow::anyhow!("the MCP session ended: {error:?}"))?;
        Ok(())
    }

    /// The tools this server advertises, with what each one needs.
    #[must_use]
    pub fn capabilities_report() -> CapabilitiesReport {
        let tools = Self::tool_router()
            .list_all()
            .into_iter()
            .map(|tool| {
                let name = tool.name.to_string();
                ToolReport {
                    needs_qgis_backend: NEEDS_QGIS.contains(&name.as_str()),
                    description: tool
                        .description
                        .map_or_else(String::new, |text| text.to_string()),
                    name,
                }
            })
            .collect();
        CapabilitiesReport {
            server: SERVER_NAME.to_string(),
            version: qgis_render::VERSION.to_string(),
            tools,
            note: "tools with needs_qgis_backend = true fail until qgis-render gains a QGIS backend"
                .to_string(),
        }
    }

    /// Describe a coordinate reference system.
    ///
    /// # Errors
    ///
    /// Returns an MCP `invalid params` error for a malformed code.
    pub fn crs_info_report(auth_id: &str) -> Result<CrsReport, ErrorData> {
        let crs = Crs::from_auth_id(auth_id).map_err(invalid_params)?;
        let units = match crs.units() {
            qgis_render::Units::Degrees => "degrees",
            qgis_render::Units::Meters => "meters",
            qgis_render::Units::Unknown => "unknown",
        };
        Ok(CrsReport {
            name: crs.name().map(str::to_string),
            units: units.to_string(),
            geographic: crs.is_geographic(),
            auth_id: crs.auth_id().to_string(),
        })
    }

    /// Count the tiles that cover an area.
    ///
    /// # Errors
    ///
    /// Returns an MCP `invalid params` error for malformed bounds or zooms.
    pub fn plan_tiles_report(bounds: &str, zoom: &str) -> Result<TilePlanReport, ErrorData> {
        let extent = Extent::parse(bounds).map_err(invalid_params)?;
        let zooms = ZoomRange::parse(zoom).map_err(invalid_params)?;
        let plan = TilePlan::new(extent, zooms).map_err(invalid_params)?;
        Ok(TilePlanReport {
            levels: plan
                .levels()
                .into_iter()
                .map(|level| ZoomLevelReport {
                    zoom: level.zoom,
                    x_min: level.x_min,
                    x_max: level.x_max,
                    y_min: level.y_min,
                    y_max: level.y_max,
                    tiles: level.tile_count(),
                })
                .collect(),
            total_tiles: plan.tile_count(),
            bounds: extent.to_string(),
            zoom: zoom.trim().to_string(),
        })
    }

    /// Describe a project file, without needing QGIS.
    ///
    /// # Errors
    ///
    /// Returns an MCP `invalid params` error when the file is missing or is
    /// not a QGIS project.
    pub fn project_info_report(project: &str) -> Result<ProjectReport, ErrorData> {
        let opened = Project::open(project).map_err(invalid_params)?;
        let info = opened.info().map_err(internal_error)?;
        Ok(ProjectReport {
            format: info.format.extension().to_string(),
            size_bytes: info.size_bytes,
            crs: info.crs.map(|crs| crs.auth_id().to_string()),
            layer_count: info.layer_count,
            note: info.note,
            path: info.path.display().to_string(),
        })
    }

    /// Check that a render request is well-formed, and build the settings.
    ///
    /// # Errors
    ///
    /// Returns an MCP `invalid params` error for a bad path, extent, CRS or
    /// output format.
    pub fn render_settings(
        params: &RenderMapParams,
    ) -> Result<(Project, RenderSettings), ErrorData> {
        let project = Project::open(&params.project).map_err(invalid_params)?;
        let mut settings = RenderSettings::new(&params.output).map_err(invalid_params)?;
        match (params.width, params.height) {
            (Some(width), Some(height)) => settings = settings.with_size(width, height),
            (Some(width), None) => settings = settings.with_size(width, settings.height),
            (None, Some(height)) => settings = settings.with_size(settings.width, height),
            (None, None) => {}
        }
        if let Some(dpi) = params.dpi {
            settings = settings.with_dpi(dpi);
        }
        if let Some(crs) = &params.crs {
            settings = settings.with_crs(Crs::from_auth_id(crs).map_err(invalid_params)?);
        }
        if let Some(extent) = &params.extent {
            settings = settings.with_extent(Extent::parse(extent).map_err(invalid_params)?);
        }
        if let Some(layers) = &params.layers {
            settings = settings.with_layers(split_list(layers));
        }
        if let Some(layout) = &params.layout {
            settings = settings.with_layout(layout.clone());
        }
        Ok((project, settings))
    }

    /// Check that an export request is well-formed.
    ///
    /// # Errors
    ///
    /// Returns an MCP `invalid params` error for a bad path, an empty layer
    /// name or a malformed bounding box.
    pub fn export_request(params: &ExportFeaturesParams) -> Result<(Project, Extent), ErrorData> {
        let project = Project::open(&params.project).map_err(invalid_params)?;
        let bbox = match &params.bbox {
            Some(bbox) => Extent::parse(bbox).map_err(invalid_params)?,
            None => Extent::new(-180.0, -90.0, 180.0, 90.0),
        };
        if params.layer.trim().is_empty() {
            return Err(ErrorData::invalid_params("layer must not be empty", None));
        }
        Ok((project, bbox))
    }
}

// ── MCP surface ───────────────────────────────────────────────────────────────

#[tool_router]
impl QgisMcpServer {
    #[tool(
        description = "List the qgis-rs tools and say which ones need the QGIS backend. Call this first."
    )]
    fn capabilities(&self) -> Result<String, ErrorData> {
        report(&Self::capabilities_report())
    }

    #[tool(description = "Describe a coordinate reference system: its name, units and whether it is geographic.")]
    fn crs_info(
        &self,
        Parameters(params): Parameters<CrsInfoParams>,
    ) -> Result<String, ErrorData> {
        report(&Self::crs_info_report(&params.auth_id)?)
    }

    #[tool(description = "Count and enumerate the XYZ tiles that cover an EPSG:4326 area over a range of zoom levels.")]
    fn plan_tiles(
        &self,
        Parameters(params): Parameters<PlanTilesParams>,
    ) -> Result<String, ErrorData> {
        report(&Self::plan_tiles_report(&params.bounds, &params.zoom)?)
    }

    #[tool(description = "Describe a QGIS project file: its format, size and where to find it. Layer details need the QGIS backend.")]
    fn project_info(
        &self,
        Parameters(params): Parameters<ProjectInfoParams>,
    ) -> Result<String, ErrorData> {
        report(&Self::project_info_report(&params.project)?)
    }

    #[tool(description = "Render a QGIS project to an image. Needs the QGIS backend.")]
    fn render_map(
        &self,
        Parameters(params): Parameters<RenderMapParams>,
    ) -> Result<String, ErrorData> {
        let (_project, _settings) = Self::render_settings(&params)?;
        Err(internal_error(RenderError::Unimplemented {
            feature: "rendering a project",
        }))
    }

    #[tool(description = "Export a layer's features to GeoJSON or CSV. Needs the QGIS backend.")]
    fn export_features(
        &self,
        Parameters(params): Parameters<ExportFeaturesParams>,
    ) -> Result<String, ErrorData> {
        let (_project, _bbox) = Self::export_request(&params)?;
        Err(internal_error(RenderError::Unimplemented {
            feature: "exporting features",
        }))
    }
}

#[tool_handler(
    router = Self::tool_router(),
    name = "qgis-cli",
    instructions = "qgis-rs exposes a QGIS rendering engine as tools. Call `capabilities` first to see which tools are live."
)]
impl rmcp::ServerHandler for QgisMcpServer {}

// ── helpers ───────────────────────────────────────────────────────────────────

fn report<T: serde::Serialize>(value: &T) -> Result<String, ErrorData> {
    serde_json::to_string_pretty(value).map_err(internal_error)
}

fn split_list(text: &str) -> Vec<String> {
    text.split(',')
        .map(str::trim)
        .filter(|item| !item.is_empty())
        .map(str::to_string)
        .collect()
}

fn invalid_params(error: RenderError) -> ErrorData {
    ErrorData::invalid_params(error.to_string(), None)
}

fn internal_error<E: std::fmt::Debug>(error: E) -> ErrorData {
    ErrorData::internal_error(format!("{error:?}"), None)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn project_file(name: &str) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join("qgis-mcp-tests");
        std::fs::create_dir_all(&dir).expect("create dir");
        let path = dir.join(name);
        std::fs::write(&path, b"<qgis></qgis>").expect("write");
        path
    }

    #[test]
    fn advertises_exactly_the_expected_tools() {
        let mut names: Vec<String> = QgisMcpServer::tool_router()
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
        for tool in QgisMcpServer::tool_router().list_all() {
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
        let info =
            QgisMcpServer::project_info_report(path.to_str().expect("utf-8")).expect("project");
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
}
