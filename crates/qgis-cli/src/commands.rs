//! Subcommand implementations.
//!
//! Argument parsing is validated here and the request is handed to
//! `qgis-render` / `qgis-server`. Anything that needs `libqgis_core` bubbles up
//! [`qgis_render::Error::Unimplemented`], which `main` turns into a one-line
//! error and a non-zero exit code.

use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};
use qgis_render::{Extent, Project, RenderSettings, TilePlan, ZoomRange};
use qgis_server::{Server, ServerConfig};

use crate::cli::{BatchArgs, Command, ExportArgs, InfoArgs, RenderArgs, ServeArgs, TilesArgs};

/// Dispatch a parsed subcommand.
///
/// # Errors
///
/// Returns whatever the subcommand failed with.
pub fn run(command: Command) -> Result<()> {
    match command {
        Command::Render(args) => render(args),
        Command::Tiles(args) => tiles(args),
        Command::Batch(args) => batch(args),
        Command::Info(args) => info(args),
        Command::Serve(args) => serve(args),
        Command::Export(args) => export(args),
        #[cfg(feature = "mcp")]
        Command::Mcp(args) => mcp(args),
    }
}

fn render(args: RenderArgs) -> Result<()> {
    let project = open_project(&args.project)?;
    let mut settings = RenderSettings::new(&args.output)
        .with_context(|| format!("cannot use {} as output", args.output.display()))?;

    // Read the current size before consuming `settings`.
    let width = args.width.unwrap_or(settings.width);
    let height = args.height.unwrap_or(settings.height);
    settings = settings.with_size(width, height);
    if let Some(dpi) = args.dpi {
        settings = settings.with_dpi(dpi);
    }
    if let Some(crs) = &args.crs {
        settings = settings.with_crs(parse_crs(crs)?);
    }
    if let Some(extent) = &args.extent {
        settings = settings.with_extent(Extent::parse(extent)?);
    }
    if let Some(layers) = &args.layers {
        settings = settings.with_layers(split_list(layers));
    }
    if let Some(layout) = &args.layout {
        settings = settings.with_layout(layout.clone());
    }

    let rendered = project.render(&settings)?;
    println!(
        "wrote {} ({} bytes)",
        rendered.path.display(),
        rendered.bytes
    );
    Ok(())
}

fn tiles(args: TilesArgs) -> Result<()> {
    let _project = open_project(&args.project)?;
    let bounds = Extent::parse(&args.bounds)
        .with_context(|| format!("cannot read --bounds {:?}", args.bounds))?;
    let zooms = ZoomRange::parse(&args.zoom)
        .with_context(|| format!("cannot read --zoom {:?}", args.zoom))?;
    let plan = TilePlan::new(bounds, zooms)?;

    if args.dry_run {
        for level in plan.levels() {
            println!(
                "z={:<3} x {}..{}  y {}..{}  {} tiles",
                level.zoom,
                level.x_min,
                level.x_max,
                level.y_min,
                level.y_max,
                level.tile_count()
            );
        }
        println!(
            "Would render {} tiles across zoom levels {}",
            plan.tile_count(),
            args.zoom
        );
        return Ok(());
    }

    bail!("tile rendering needs the QGIS backend, which is not wired up yet")
}

fn batch(args: BatchArgs) -> Result<()> {
    let _project = open_project(&args.project)?;
    let text = std::fs::read_to_string(&args.extents)
        .with_context(|| format!("cannot read {}", args.extents.display()))?;
    let rows = parse_extent_rows(&text)
        .with_context(|| format!("cannot parse {}", args.extents.display()))?;

    for (name, extent) in &rows {
        println!("{name}: {extent}");
    }
    println!(
        "{} extent(s) from {}, output in {}",
        rows.len(),
        args.extents.display(),
        args.output.display()
    );
    bail!("batch rendering needs the QGIS backend, which is not wired up yet")
}

/// Parse a `name,minx,miny,maxx,maxy` CSV, as accepted by `batch --extents`.
///
/// Blank lines and `#` comments are skipped, as is a `name,...` header row.
///
/// # Errors
///
/// Returns an error naming the offending line.
pub fn parse_extent_rows(text: &str) -> Result<Vec<(String, Extent)>> {
    let mut rows = Vec::new();
    for (index, line) in text.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let mut fields = line.split(',').map(str::trim);
        let name = fields.next().unwrap_or_default().to_string();
        if index == 0 && name.eq_ignore_ascii_case("name") {
            continue;
        }
        let mut values = [0.0f64; 4];
        for slot in &mut values {
            let field = fields.next().ok_or_else(|| {
                anyhow::anyhow!("line {}: expected \"name,minx,miny,maxx,maxy\"", index + 1)
            })?;
            *slot = field
                .parse::<f64>()
                .map_err(|_| anyhow::anyhow!("line {}: {:?} is not a number", index + 1, field))?;
        }
        let extent = Extent::new(values[0], values[1], values[2], values[3]);
        if !extent.is_valid() {
            bail!("line {}: extent {extent} is not ordered min,max", index + 1);
        }
        rows.push((name, extent));
    }
    Ok(rows)
}

fn info(args: InfoArgs) -> Result<()> {
    let project = open_project(&args.project)?;
    let info = project.info()?;

    if args.json {
        println!(
            "{}",
            serde_json::to_string_pretty(&info).context("cannot serialise the project info")?
        );
        return Ok(());
    }

    println!("path:    {}", info.path.display());
    println!("format:  {}", info.format.extension());
    println!("size:    {} bytes", info.size_bytes);
    println!(
        "crs:     {}",
        info.crs.as_ref().map_or("unknown", |crs| crs.auth_id())
    );
    println!(
        "layers:  {}",
        info.layer_count
            .map_or_else(|| "unknown".to_string(), |count| count.to_string())
    );
    if let Some(note) = &info.note {
        println!("note:    {note}");
    }
    Ok(())
}

fn serve(args: ServeArgs) -> Result<()> {
    let mut config = ServerConfig::new(args.port).with_cors(!args.no_cors);
    config.host = args.host.clone();
    config.cache_mb = args.cache_mb;

    match (args.project, args.projects_dir) {
        (Some(project), None) => config = config.with_project(project),
        (None, Some(projects_dir)) => config = config.with_projects_dir(projects_dir),
        (None, None) => bail!("give a project file or --projects-dir"),
        (Some(_), Some(_)) => bail!("give either a project file or --projects-dir, not both"),
    }

    let server = Server::new(config);
    println!(
        "serving {} on http://{}/",
        what_is_served(&server),
        server.address()
    );
    println!("  /wms  /wfs  /tiles/{{z}}/{{x}}/{{y}}.png  /collections  /health");
    server.serve()?;
    Ok(())
}

fn what_is_served(server: &Server) -> String {
    let config = server.config();
    if let Some(project) = &config.project {
        return project.display().to_string();
    }
    if let Some(projects_dir) = &config.projects_dir {
        return format!("every project in {}", projects_dir.display());
    }
    "nothing".to_string()
}

fn export(args: ExportArgs) -> Result<()> {
    let project = open_project(&args.project)?;
    if args.layer.trim().is_empty() {
        bail!("--layer must not be empty");
    }
    if let Some(bbox) = &args.bbox {
        Extent::parse(bbox).with_context(|| format!("cannot read --bbox {:?}", bbox))?;
    }
    let output = args
        .output
        .unwrap_or_else(|| PathBuf::from(format!("{}.geojson", args.layer)));
    let format = output
        .extension()
        .and_then(|extension| extension.to_str())
        .unwrap_or("geojson");

    let written = project.export_layer(&args.layer, format)?;
    println!("wrote {}", written.display());
    Ok(())
}

/// Start the MCP server on stdio.
///
/// # Errors
///
/// Returns a transport or session failure from the server.
#[cfg(feature = "mcp")]
pub fn mcp(args: crate::cli::McpArgs) -> Result<()> {
    if args.list_tools {
        for tool in qgis_mcp::QgisMcpServer::capabilities_report().tools {
            let marker = if tool.needs_qgis_backend {
                "[needs QGIS] "
            } else {
                ""
            };
            println!("{:<16} {marker}{}", tool.name, tool.description);
        }
        return Ok(());
    }

    // The protocol owns stdout, so every diagnostic goes to stderr.
    eprintln!(
        "qgis-cli {} MCP server on stdio; close stdin to stop",
        env!("CARGO_PKG_VERSION")
    );
    let runtime = tokio::runtime::Runtime::new().context("cannot start the Tokio runtime")?;
    runtime.block_on(qgis_mcp::QgisMcpServer::new().serve_stdio())
}

fn open_project(path: &Path) -> Result<Project> {
    Project::open(path).with_context(|| format!("cannot open {}", path.display()))
}

fn parse_crs(text: &str) -> Result<qgis_render::Crs> {
    qgis_render::Crs::from_auth_id(text).with_context(|| format!("cannot read --crs {:?}", text))
}

fn split_list(text: &str) -> Vec<String> {
    text.split(',')
        .map(str::trim)
        .filter(|item| !item.is_empty())
        .map(str::to_string)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_the_documented_extents_csv() {
        let text = "\
# name,minx,miny,maxx,maxy
name,minx,miny,maxx,maxy

berlin,13.08,52.33,13.76,52.68
paris,2.22,48.81,2.47,48.91
";
        let rows = parse_extent_rows(text).expect("valid csv");
        assert_eq!(rows.len(), 2);
        assert_eq!(rows[0].0, "berlin");
        assert_eq!(rows[0].1, Extent::new(13.08, 52.33, 13.76, 52.68));
        assert_eq!(rows[1].0, "paris");
    }

    #[test]
    fn rejects_malformed_extent_rows() {
        assert!(parse_extent_rows("berlin,13.08,52.33").is_err());
        assert!(parse_extent_rows("berlin,13.08,52.33,13.76,x").is_err());
        assert!(parse_extent_rows("berlin,13.76,52.33,13.08,52.68").is_err());
        assert!(parse_extent_rows("").expect("no rows").is_empty());
    }

    #[test]
    fn splits_layer_lists() {
        assert_eq!(
            split_list("buildings, roads ,,"),
            vec!["buildings".to_string(), "roads".to_string()]
        );
    }

    #[test]
    fn describes_what_a_server_would_serve() {
        let single = Server::new(ServerConfig::new(8080).with_project("map.qgs"));
        assert_eq!(what_is_served(&single), "map.qgs");

        let multi = Server::new(ServerConfig::new(8080).with_projects_dir("./maps"));
        assert_eq!(what_is_served(&multi), "every project in ./maps");

        let none = Server::new(ServerConfig::new(8080));
        assert_eq!(what_is_served(&none), "nothing");
    }

    #[test]
    fn a_dry_run_tile_plan_counts_tiles() {
        let result = tiles(TilesArgs {
            project: project_path(),
            zoom: "10-14".to_string(),
            bounds: "14,50,15,51".to_string(),
            output: PathBuf::from("tiles/"),
            format: "png".to_string(),
            tile_size: 256,
            parallel: 4,
            dry_run: true,
        });
        assert!(result.is_ok(), "{result:?}");

        let real_run = tiles(TilesArgs {
            project: project_path(),
            zoom: "10".to_string(),
            bounds: "14,50,15,51".to_string(),
            output: PathBuf::from("tiles/"),
            format: "png".to_string(),
            tile_size: 256,
            parallel: 4,
            dry_run: false,
        });
        let error = real_run.expect_err("needs the QGIS backend");
        assert!(error.to_string().contains("QGIS backend"));
    }

    fn project_path() -> PathBuf {
        let dir = std::env::temp_dir().join("qgis-cli-tests");
        std::fs::create_dir_all(&dir).expect("create dir");
        let path = dir.join("map.qgs");
        std::fs::write(&path, b"<qgis></qgis>").expect("write");
        path
    }
}
