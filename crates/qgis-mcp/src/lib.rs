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
//! Pure planning tools and native QGIS tools share one MCP surface. Rendering
//! and feature export cross the RFC 19 native-manager boundary, which owns all
//! QGIS objects and returns path-based artifact metadata rather than bytes.
//!
//! The `_report` helpers are the pure half of each tool: they take plain
//! arguments and return typed values, which is what the tests exercise.

use qgis_render::{
    Crs, Error as RenderError, Extent, Project, RenderSettings, TilePlan, ZoomRange,
};
use rmcp::{
    handler::server::{router::tool::ToolRouter, wrapper::Parameters},
    tool, tool_handler, tool_router,
    transport::stdio,
    ErrorData, ServiceExt,
};

/// The implementation name reported during the MCP handshake.
pub const SERVER_NAME: &str = "qgis-cli";


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
    #[schemars(
        description = "Where to write the image; the extension picks the format (.png, .jpg, .jpeg, or .webp)."
    )]
    pub output: String,
    #[schemars(
        description = "Area to render in EPSG:4326, as \"minx,miny,maxx,maxy\". Defaults to the full extent."
    )]
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
    /// Whether the loaded native backend serves this tool.
    pub available: bool,
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
    /// Backend selected for this server process.
    pub backend: String,
    /// QGIS version when the native backend initialized.
    pub qgis_version: Option<String>,
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

    /// The tool router `#[tool_router]` generated for this server.
    ///
    /// The macro's own `tool_router()` is private to the crate, and the tests
    /// live outside it (`tests/tools.rs`), so the advertised tool list — which
    /// is this server's contract with every MCP client — is reachable here.
    #[must_use]
    pub fn tools() -> ToolRouter<Self> {
        Self::tool_router()
    }

    /// The tools this server advertises and whether the loaded backend serves them.
    #[must_use]
    pub fn capabilities_report() -> CapabilitiesReport {
        let backend = native_backend();
        let tools = Self::tool_router()
            .list_all()
            .into_iter()
            .map(|tool| {
                let name = tool.name.to_string();
                let available = match name.as_str() {
                    "render_map" | "export_features" => backend.supports(&name),
                    _ => true,
                };
                ToolReport {
                    available,
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
            backend: backend.name,
            qgis_version: backend.qgis_version,
            tools,
            note: "capabilities are computed from the native manager loaded by this process"
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
        // Read the current size before consuming `settings`.
        let width = params.width.unwrap_or(settings.width);
        let height = params.height.unwrap_or(settings.height);
        settings = settings.with_size(width, height);
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
        if !settings.format.is_raster() {
            return Err(ErrorData::invalid_params(
                "the native map renderer currently writes raster images (png, jpg, jpeg, or webp)",
                None,
            ));
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
        description = "List the qgis-rs tools and report availability from the loaded backend. Call this first."
    )]
    pub fn capabilities(&self) -> Result<String, ErrorData> {
        report(&Self::capabilities_report())
    }

    #[tool(
        description = "Describe a coordinate reference system: its name, units and whether it is geographic."
    )]
    pub fn crs_info(
        &self,
        Parameters(params): Parameters<CrsInfoParams>,
    ) -> Result<String, ErrorData> {
        report(&Self::crs_info_report(&params.auth_id)?)
    }

    #[tool(
        description = "Count and enumerate the XYZ tiles that cover an EPSG:4326 area over a range of zoom levels."
    )]
    pub fn plan_tiles(
        &self,
        Parameters(params): Parameters<PlanTilesParams>,
    ) -> Result<String, ErrorData> {
        report(&Self::plan_tiles_report(&params.bounds, &params.zoom)?)
    }

    #[tool(
        description = "Describe a QGIS project file: its format, size and where to find it."
    )]
    pub fn project_info(
        &self,
        Parameters(params): Parameters<ProjectInfoParams>,
    ) -> Result<String, ErrorData> {
        report(&Self::project_info_report(&params.project)?)
    }

    #[tool(description = "Render a QGIS project to a path-based image artifact using the loaded native QGIS backend.")]
    pub fn render_map(
        &self,
        Parameters(params): Parameters<RenderMapParams>,
    ) -> Result<String, ErrorData> {
        let (_project, settings) = Self::render_settings(&params)?;
        let payload = serde_json::json!({
            "project": params.project,
            "output": settings.output,
            "width": settings.width,
            "height": settings.height,
            "dpi": settings.dpi,
            "crs": params.crs,
            "extent": params.extent,
            "layers": settings.layers,
            "layout": params.layout,
        });
        report(&native_call("render_map", payload)?)
    }

    #[tool(description = "Export a QGIS vector layer to a path-based GeoJSON or CSV artifact using the loaded native QGIS backend.")]
    pub fn export_features(
        &self,
        Parameters(params): Parameters<ExportFeaturesParams>,
    ) -> Result<String, ErrorData> {
        let (project, bbox) = Self::export_request(&params)?;
        let output = params.output.clone().unwrap_or_else(|| {
            project
                .path()
                .parent()
                .unwrap_or_else(|| std::path::Path::new("."))
                .join(format!("{}.geojson", params.layer))
                .display()
                .to_string()
        });
        let fields = params
            .fields
            .as_deref()
            .map(split_list)
            .unwrap_or_default();
        let payload = serde_json::json!({
            "project": project.path(),
            "layer": params.layer,
            "output": output,
            "filter": params.filter,
            "bbox": params.bbox.unwrap_or_else(|| bbox.to_string()),
            "fields": fields,
        });
        report(&native_call("export_features", payload)?)
    }
}

#[tool_handler(
    router = Self::tool_router(),
    name = "qgis-cli",
    instructions = "qgis-rs exposes a QGIS rendering engine as tools. Call `capabilities` first to see which tools are live."
)]
impl rmcp::ServerHandler for QgisMcpServer {}

// ── helpers ───────────────────────────────────────────────────────────────────

struct NativeBackend {
    operations: Vec<String>,
    name: String,
    qgis_version: Option<String>,
}

impl NativeBackend {
    fn supports(&self, operation: &str) -> bool {
        self.operations.iter().any(|name| name == operation)
    }
}

fn native_backend() -> NativeBackend {
    let init = native_call("app_init", serde_json::Value::Null);
    if init.is_err() {
        return NativeBackend {
            operations: Vec::new(),
            name: "unavailable".to_string(),
            qgis_version: None,
        };
    }
    match native_call("api_describe", serde_json::Value::Null) {
        Ok(info) => NativeBackend {
            operations: info["operations"]
                .as_array()
                .map(|operations| {
                    operations
                        .iter()
                        .filter_map(|name| name.as_str().map(str::to_string))
                        .collect()
                })
                .unwrap_or_default(),
            name: info["engine"]
                .as_str()
                .unwrap_or("qgis-native-manager")
                .to_string(),
            qgis_version: info["qgis_version"].as_str().map(str::to_string),
        },
        Err(_) => NativeBackend {
            operations: Vec::new(),
            name: "unavailable".to_string(),
            qgis_version: None,
        },
    }
}

fn native_call(
    operation: &str,
    payload: serde_json::Value,
) -> Result<serde_json::Value, ErrorData> {
    if operation != "app_init" {
        let init = serde_json::json!({
            "transport_version": 1,
            "operation": "app_init",
            "payload": null,
        });
        let init_response: serde_json::Value = serde_json::from_str(
            &qgis_sys::native_manager_ffi::invoke(&init.to_string()),
        )
        .map_err(internal_error)?;
        if init_response["ok"].as_bool() != Some(true) {
            return Err(internal_error(init_response["result"].clone()));
        }
    }
    let request = serde_json::json!({
        "transport_version": 1,
        "operation": operation,
        "payload": payload,
    });
    let response: serde_json::Value = serde_json::from_str(
        &qgis_sys::native_manager_ffi::invoke(&request.to_string()),
    )
    .map_err(internal_error)?;
    if response["ok"].as_bool() == Some(true) {
        return Ok(response["result"].clone());
    }
    let result = &response["result"];
    let message = result["error"]
        .as_str()
        .unwrap_or("native manager rejected the request");
    match result["kind"].as_str() {
        Some("invalid_payload") | Some("invalid_object_id") => {
            Err(ErrorData::invalid_params(message.to_string(), None))
        }
        _ => Err(internal_error(message.to_string())),
    }
}

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
