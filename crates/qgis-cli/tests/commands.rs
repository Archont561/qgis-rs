//! The command implementations that need no QGIS backend: the batch CSV
//! parser, the `--layers` splitter, what `serve` says it would serve, and the
//! `tiles --dry-run` plan.

use std::path::PathBuf;

use qgis_cli::cli::TilesArgs;
use qgis_cli::commands::{parse_extent_rows, split_list, tiles, what_is_served};
use qgis_render::Extent;
use qgis_server::{Server, ServerConfig};

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
