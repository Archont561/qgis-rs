//! The command implementations that need no QGIS backend: the batch CSV
//! parser, the `--layers` splitter, what `serve` says it would serve, and the
//! `tiles --dry-run` plan.
//!
//! The project file every tile test needs is a fixture, and the two argument
//! sets the tile tests used to build by hand come from a `tiles_args` fixture
//! that each test adjusts with struct update syntax.

use std::path::PathBuf;

use qgis_cli::cli::TilesArgs;
use qgis_cli::commands::{parse_extent_rows, split_list, tiles, what_is_served};
use qgis_render::Extent;
use qgis_server::{Server, ServerConfig};
use rstest::{fixture, rstest};

/// A minimal project on disk, which `tiles` only has to be able to open.
#[fixture]
fn project_path() -> PathBuf {
    let dir = std::env::temp_dir().join("qgis-cli-tests");
    std::fs::create_dir_all(&dir).expect("create dir");
    let path = dir.join("map.qgs");
    std::fs::write(&path, b"<qgis></qgis>").expect("write");
    path
}

/// The documented tile request: central Europe, z10-14, as a dry run.
#[fixture]
fn tiles_args(project_path: PathBuf) -> TilesArgs {
    TilesArgs {
        project: project_path,
        zoom: "10-14".to_string(),
        bounds: "14,50,15,51".to_string(),
        output: PathBuf::from("tiles/"),
        format: "png".to_string(),
        tile_size: 256,
        parallel: 4,
        dry_run: true,
    }
}

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

#[rstest]
#[case::too_few_columns("berlin,13.08,52.33")]
#[case::not_a_number("berlin,13.08,52.33,13.76,x")]
#[case::reversed_extent("berlin,13.76,52.33,13.08,52.68")]
fn rejects_malformed_extent_rows(#[case] row: &str) {
    assert!(parse_extent_rows(row).is_err(), "{row:?} should fail");
}

#[test]
fn an_empty_csv_has_no_rows() {
    assert!(parse_extent_rows("").expect("no rows").is_empty());
}

#[test]
fn splits_layer_lists() {
    assert_eq!(
        split_list("buildings, roads ,,"),
        vec!["buildings".to_string(), "roads".to_string()]
    );
}

#[rstest]
#[case::single(ServerConfig::new(8080).with_project("map.qgs"), "map.qgs")]
#[case::multi(
    ServerConfig::new(8080).with_projects_dir("./maps"),
    "every project in ./maps"
)]
#[case::unconfigured(ServerConfig::new(8080), "nothing")]
fn describes_what_a_server_would_serve(#[case] config: ServerConfig, #[case] expected: &str) {
    assert_eq!(what_is_served(&Server::new(config)), expected);
}

#[rstest]
fn a_dry_run_tile_plan_counts_tiles(tiles_args: TilesArgs) {
    let result = tiles(tiles_args);
    assert!(result.is_ok(), "{result:?}");
}

#[rstest]
fn a_real_tile_run_stops_at_the_backend(tiles_args: TilesArgs) {
    let error = tiles(TilesArgs {
        zoom: "10".to_string(),
        dry_run: false,
        ..tiles_args
    })
    .expect_err("needs the QGIS backend");
    assert!(error.to_string().contains("QGIS backend"));
}
