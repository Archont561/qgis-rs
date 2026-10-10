//! Command-line surface of `qgis-cli`.
//!
//! The shapes here mirror `.knowledge/api-design.md` section 2, so the docs,
//! the CLI and the MCP tools stay in step.

use std::path::PathBuf;

use clap::{Parser, Subcommand, ValueEnum};

/// Render, tile, inspect and serve QGIS projects.
#[derive(Debug, Parser)]
#[command(name = "qgis-cli", version, about, long_about = None)]
pub struct Cli {
    /// The command to run.
    #[command(subcommand)]
    pub command: Command,
}

/// Every `qgis-cli` subcommand.
#[derive(Debug, Subcommand)]
pub enum Command {
    /// Validate pure GIS domain input without loading QGIS
    Validate(ValidateArgs),
    /// Plan deterministic work from input alone, without a project or QGIS
    Plan(PlanArgs),
    /// Report CLI, engine, transport and backend versions
    Version(DiscoveryArgs),
    /// Describe engine capabilities and the parsed command surface
    Capabilities(DiscoveryArgs),
    /// Diagnose engine readiness and optional native backend availability
    Doctor(DiscoveryArgs),
    /// Render a project to an image
    Render(RenderArgs),
    /// Build an XYZ tile pyramid
    Tiles(TilesArgs),
    /// Render many extents listed in a CSV file
    Batch(BatchArgs),
    /// Inspect project file metadata without parsing contents or initializing QGIS
    Inspect(InspectArgs),
    /// Describe a project
    Info(InfoArgs),
    /// Serve a project over HTTP: WMS, WFS, tiles and OGC API Features
    Serve(ServeArgs),
    /// Export a layer's features
    Export(ExportArgs),
    /// Run the Model Context Protocol server over stdio
    #[cfg(feature = "mcp")]
    Mcp(McpArgs),
}

/// `qgis-cli render <project>`
#[derive(Debug, Parser)]
pub struct RenderArgs {
    /// QGIS project to render (.qgs or .qgz)
    pub project: PathBuf,

    /// Where to write the image; the extension picks the format. `-` is stdout.
    #[arg(short, long)]
    pub output: PathBuf,

    /// Extent to render, as "minx,miny,maxx,maxy"
    #[arg(long)]
    pub extent: Option<String>,

    /// Image width in pixels
    #[arg(long)]
    pub width: Option<u32>,

    /// Image height in pixels
    #[arg(long)]
    pub height: Option<u32>,

    /// CRS to render in, e.g. EPSG:3857
    #[arg(long)]
    pub crs: Option<String>,

    /// Comma-separated list of layers to draw
    #[arg(long)]
    pub layers: Option<String>,

    /// Resolution in dots per inch
    #[arg(long)]
    pub dpi: Option<f64>,

    /// Render a print layout instead of the map canvas
    #[arg(long)]
    pub layout: Option<String>,
}

/// `qgis-cli tiles <project>`
#[derive(Debug, Parser)]
pub struct TilesArgs {
    /// QGIS project to tile (.qgs or .qgz)
    pub project: PathBuf,

    /// Zoom levels, as "12" or "10-14"
    #[arg(short, long)]
    pub zoom: String,

    /// Area to cover in EPSG:4326, as "minx,miny,maxx,maxy"
    #[arg(short, long)]
    pub bounds: String,

    /// Output directory, or an .mbtiles/.pmtiles file
    #[arg(short, long)]
    pub output: PathBuf,

    /// Tile format
    #[arg(long, default_value = "png")]
    pub format: String,

    /// Tile edge in pixels
    #[arg(long, default_value_t = 256)]
    pub tile_size: u32,

    /// Worker threads
    #[arg(long, default_value_t = 4)]
    pub parallel: usize,

    /// Count the tiles without rendering any
    #[arg(long)]
    pub dry_run: bool,
}

/// `qgis-cli batch <project>`
#[derive(Debug, Parser)]
pub struct BatchArgs {
    /// QGIS project to render (.qgs or .qgz)
    pub project: PathBuf,

    /// CSV file with "name,minx,miny,maxx,maxy" rows
    #[arg(long)]
    pub extents: PathBuf,

    /// Directory to write the renders into
    #[arg(short, long)]
    pub output: PathBuf,

    /// Zoom level to render at
    #[arg(short, long)]
    pub zoom: Option<String>,
}

/// `qgis-cli inspect <project>` — filesystem metadata, not project validation.
#[derive(Debug, Parser)]
pub struct InspectArgs {
    /// Local .qgs or .qgz file; contents are not read or validated
    pub project: PathBuf,

    /// Write a deterministic JSON report to stdout
    #[arg(long)]
    pub json: bool,
}

/// `qgis-cli info <project>`
#[derive(Debug, Parser)]
pub struct InfoArgs {
    /// QGIS project to describe (.qgs or .qgz)
    pub project: PathBuf,

    /// Print JSON instead of a human-readable summary
    #[arg(long)]
    pub json: bool,
}

/// `qgis-cli serve [project]`
#[derive(Debug, Parser)]
pub struct ServeArgs {
    /// QGIS project to serve (.qgs or .qgz)
    pub project: Option<PathBuf>,

    /// Serve every project in this directory, routed by URL prefix
    #[arg(long)]
    pub projects_dir: Option<PathBuf>,

    /// Port to listen on
    #[arg(long, default_value_t = 8080)]
    pub port: u16,

    /// Interface to bind to
    #[arg(long, default_value = "0.0.0.0")]
    pub host: String,

    /// Do not send CORS headers
    #[arg(long)]
    pub no_cors: bool,

    /// Rendered-tile cache size in megabytes
    #[arg(long, default_value_t = 256)]
    pub cache_mb: u32,
}

/// `qgis-cli export <project>`
#[derive(Debug, Parser)]
pub struct ExportArgs {
    /// QGIS project holding the layer (.qgs or .qgz)
    pub project: PathBuf,

    /// Layer to export
    #[arg(long)]
    pub layer: String,

    /// Where to write the output; the extension picks the format
    #[arg(short, long)]
    pub output: Option<PathBuf>,

    /// QGIS expression used to filter features
    #[arg(long)]
    pub filter: Option<String>,

    /// Bounding box in EPSG:4326, as "minx,miny,maxx,maxy"
    #[arg(long)]
    pub bbox: Option<String>,

    /// Comma-separated attribute names to keep
    #[arg(long)]
    pub fields: Option<String>,
}

/// `qgis-cli mcp`
#[cfg(feature = "mcp")]
#[derive(Debug, Parser)]
pub struct McpArgs {
    /// Print the tools the server offers, then exit
    #[arg(long)]
    pub list_tools: bool,
}

/// Output options for read-only discovery commands.
#[derive(Debug, Parser)]
pub struct DiscoveryArgs {
    /// Write a deterministic JSON report to stdout
    #[arg(long)]
    pub json: bool,
}

/// Pure input types supported by `validate`.
#[derive(Debug, Clone, Copy, ValueEnum)]
pub enum ValidateKind {
    /// Finite, ordered coordinates: minx,miny,maxx,maxy
    Extent,
    /// Authority-code syntax only, not CRS database recognition
    Crs,
    /// Inclusive zoom level or range within the supported domain
    Zoom,
    /// XYZ tile coordinates written as z/x/y
    Tile,
}

/// `qgis-cli validate <kind> <value>`.
#[derive(Debug, Parser)]
pub struct ValidateArgs {
    /// Domain type to validate
    #[arg(value_enum)]
    pub kind: ValidateKind,
    /// Input text; precede a leading minus with `--`
    pub value: String,
    /// Write a structured report to stdout
    #[arg(long)]
    pub json: bool,
}

/// `qgis-cli plan <what>`.
#[derive(Debug, Parser)]
pub struct PlanArgs {
    /// What to plan
    #[command(subcommand)]
    pub command: PlanCommand,
}

/// What `qgis-cli plan` can plan.
#[derive(Debug, Subcommand)]
pub enum PlanCommand {
    /// Count an XYZ tile pyramid over an extent
    Tiles(TilesPlanArgs),
}

/// `qgis-cli plan tiles`.
///
/// Separate from `tiles <project> --dry-run`, which counts the same pyramid
/// but opens a project file first. Nothing here reads a file or writes one.
#[derive(Debug, Parser)]
pub struct TilesPlanArgs {
    /// Area to cover in EPSG:4326, as "minx,miny,maxx,maxy"
    #[arg(short, long)]
    pub bounds: String,
    /// Zoom levels, as "12" or "10-14"
    #[arg(short, long)]
    pub zoom: String,
    /// Write a structured report to stdout
    #[arg(long)]
    pub json: bool,
}
