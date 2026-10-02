//! The command line as a user types it: every subcommand parses to the
//! arguments its implementation expects, and a `render` without `-o` fails at
//! the parser rather than halfway through a render.

use std::path::PathBuf;

use clap::{CommandFactory, Parser};
use qgis_cli::{Cli, Command};

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
        "qgis-cli",
        "tiles",
        "map.qgs",
        "-z",
        "10-14",
        "-b",
        "14,50,15,51",
        "-o",
        "tiles/",
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
        "qgis-cli",
        "export",
        "map.qgs",
        "--layer",
        "buildings",
        "--bbox",
        "14,50,15,51",
    ])
    .expect("valid arguments");
    assert!(matches!(cli.command, Command::Export(_)));

    let cli =
        Cli::try_parse_from(["qgis-cli", "info", "map.qgs", "--json"]).expect("valid arguments");
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
