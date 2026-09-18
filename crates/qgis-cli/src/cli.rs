//! Command-line surface of `qgis-cli`.
//!
//! The shapes here mirror `.knowledge/api-design.md` section 2, so the docs,
//! the CLI and the MCP tools stay in step.

use std::path::PathBuf;

use clap::{Parser, Subcommand};

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
    /// Render a project to an image
    Render(RenderArgs),
    /// Build an XYZ tile pyramid
    Tiles(TilesArgs),
    /// Render many extents listed in a CSV file
    Batch(BatchArgs),
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

#[cfg(test)]
mod tests {
    use super::*;
    use clap::CommandFactory;

    #[test]
    fn the_command_line_definition_is_valid() {
        Cli::command().debug_assert();
    }

    #[test]
    fn parses_render() {
        let cli = Cli::try_parse_from([
            "qgis-cli",
            "render",
            "map.qgs",
            "-o",
            "map.png",
            "--extent",
            "14,50,15,51",
            "--width",
            "2048",
            "--crs",
            "EPSG:3857",
            "--dpi",
            "300",
            "--layers",
            "buildings,roads",
        ])
        .expect("valid arguments");

        match cli.command {
            Command::Render(args) => {
                assert_eq!(args.project, PathBuf::from("map.qgs"));
                assert_eq!(args.output, PathBuf::from("map.png"));
                assert_eq!(args.extent.as_deref(), Some("14,50,15,51"));
                assert_eq!(args.width, Some(2048));
                assert_eq!(args.crs.as_deref(), Some("EPSG:3857"));
                assert_eq!(args.dpi, Some(300.0));
                assert_eq!(args.layers.as_deref(), Some("buildings,roads"));
            }
            other => panic!("expected render, got {other:?}"),
        }
    }

    #[test]
    fn parses_tiles_with_a_dry_run() {
        let cli = Cli::try_parse_from([
            "qgis-cli", "tiles", "map.qgs", "-z", "10-14", "-b", "14,50,15,51", "-o", "tiles/",
            "--dry-run",
        ])
        .expect("valid arguments");

        match cli.command {
            Command::Tiles(args) => {
                assert_eq!(args.zoom, "10-14");
                assert_eq!(args.bounds, "14,50,15,51");
                assert!(args.dry_run);
                assert_eq!(args.tile_size, 256);
                assert_eq!(args.parallel, 4);
                assert_eq!(args.format, "png");
            }
            other => panic!("expected tiles, got {other:?}"),
        }
    }

    #[test]
    fn parses_serve_defaults() {
        let cli = Cli::try_parse_from(["qgis-cli", "serve", "map.qgs"]).expect("valid arguments");
        match cli.command {
            Command::Serve(args) => {
                assert_eq!(args.port, 8080);
                assert_eq!(args.host, "0.0.0.0");
                assert!(!args.no_cors);
                assert_eq!(args.cache_mb, 256);
                assert_eq!(args.project, Some(PathBuf::from("map.qgs")));
                assert_eq!(args.projects_dir, None);
            }
            other => panic!("expected serve, got {other:?}"),
        }
    }

    #[test]
    fn parses_export_and_info() {
        let cli = Cli::try_parse_from([
            "qgis-cli", "export", "map.qgs", "--layer", "buildings", "--bbox", "14,50,15,51",
        ])
        .expect("valid arguments");
        assert!(matches!(cli.command, Command::Export(_)));

        let cli = Cli::try_parse_from(["qgis-cli", "info", "map.qgs", "--json"])
            .expect("valid arguments");
        match cli.command {
            Command::Info(args) => assert!(args.json),
            other => panic!("expected info, got {other:?}"),
        }
    }

    #[test]
    fn rejects_a_render_without_output() {
        let result = Cli::try_parse_from(["qgis-cli", "render", "map.qgs"]);
        assert!(result.is_err());
    }

    #[cfg(feature = "mcp")]
    #[test]
    fn parses_the_mcp_subcommand() {
        let cli = Cli::try_parse_from(["qgis-cli", "mcp"]).expect("valid arguments");
        match cli.command {
            Command::Mcp(args) => assert!(!args.list_tools),
            other => panic!("expected mcp, got {other:?}"),
        }

        let cli = Cli::try_parse_from(["qgis-cli", "mcp", "--list-tools"]).expect("valid");
        match cli.command {
            Command::Mcp(args) => assert!(args.list_tools),
            other => panic!("expected mcp, got {other:?}"),
        }
    }
}
