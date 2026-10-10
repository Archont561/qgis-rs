//! Tile arithmetic — the part of this repository with exact, checkable
//! answers. The pyramid over `14,50,15,51` at z10-14 is 4568 tiles, and the
//! same numbers are asserted again from Python and from JavaScript.

use proptest::prelude::*;
use qgis_render::*;
use rstest::{fixture, rstest};

/// Central Europe: the bounds the CLI docs use.
#[fixture]
fn europe_bounds() -> Extent {
    Extent::parse("14,50,15,51").expect("valid extent")
}

#[test]
fn locates_the_origin_tile() {
    assert_eq!(Tile::from_lon_lat(0, 0.0, 0.0), Tile::new(0, 0, 0));
    assert_eq!(Tile::from_lon_lat(10, 0.0, 0.0), Tile::new(10, 512, 512));
}

#[test]
fn tile_bounds_are_the_inverse_of_tile_lookup() {
    let tile = Tile::new(10, 551, 342);
    let extent = tile.bounds();
    assert_eq!(extent.min_x, 13.710_937_5);
    assert_eq!(extent.max_x, 14.0625);
    assert!((extent.max_y - 51.179_342_979_289_27).abs() < 1e-12);
    assert_eq!(Tile::from_lon_lat(10, 13.9, 51.1), tile);
}

#[rstest]
fn plans_a_single_zoom_level(europe_bounds: Extent) {
    let plan = TilePlan::new(europe_bounds, ZoomRange::parse("10").expect("valid")).expect("valid");
    let level = plan.level(10);
    assert_eq!(
        level,
        ZoomLevelPlan {
            zoom: 10,
            x_min: 551,
            x_max: 554,
            y_min: 342,
            y_max: 347,
        }
    );
    assert_eq!(level.tile_count(), 24);
    assert_eq!(plan.tile_count(), 24);
    assert_eq!(plan.iter().count(), 24);
    assert_eq!(plan.iter().next(), Some(Tile::new(10, 551, 342)));
}

#[rstest]
fn plans_a_zoom_range(europe_bounds: Extent) {
    let plan =
        TilePlan::new(europe_bounds, ZoomRange::parse("10-14").expect("valid")).expect("valid");
    assert_eq!(plan.zooms.count(), 5);
    assert_eq!(plan.levels().len(), 5);
    assert_eq!(plan.tile_count(), 4568);
    assert_eq!(plan.iter().count(), 4568);
}

#[test]
fn a_point_covers_exactly_one_tile() {
    let point = Extent::parse("14.5,50.5,14.5,50.5").expect("valid extent");
    let plan = TilePlan::new(point, ZoomRange::new(12, 12).expect("valid")).expect("valid");
    assert_eq!(plan.tile_count(), 1);
}

#[test]
fn the_whole_world_at_zoom_two_is_sixteen_tiles() {
    let world = Extent::new(-180.0, -MAX_LATITUDE, 180.0, MAX_LATITUDE);
    let plan = TilePlan::new(world, ZoomRange::new(2, 2).expect("valid")).expect("valid");
    assert_eq!(plan.tile_count(), 16);
    assert_eq!(Tile::tiles_at_zoom(2), 16);
}

#[test]
fn zoom_range_parsing() {
    assert_eq!(
        ZoomRange::parse("12").expect("valid"),
        ZoomRange { min: 12, max: 12 }
    );
    assert_eq!(
        ZoomRange::parse("10-14").expect("valid"),
        ZoomRange { min: 10, max: 14 }
    );
    for text in ["14-10", "a", "", "10-", "-10", "30"] {
        assert!(ZoomRange::parse(text).is_err(), "{text:?} should fail");
    }
}

/// The shape a plan takes when it crosses a boundary.
///
/// [`ZoomLevelPlan`] computes its count instead of storing it, so serialising a
/// level drops the number and every consumer re-derives it. Three consumers
/// did, and drifted: the engine said `tile_count`, MCP said `total_tiles`, and
/// MCP's per-level `tiles` was a count where the engine's top-level `tiles` is
/// the enumerated array. [`TilePlanReport`] is the single definition the engine
/// wire protocol, the MCP tool and `qgis-cli plan tiles` all emit.
#[rstest]
fn a_report_carries_the_counts_a_serialised_level_would_lose(europe_bounds: Extent) {
    let plan =
        TilePlan::new(europe_bounds, ZoomRange::parse("10-14").expect("valid")).expect("valid");

    let report = plan.report();

    assert_eq!(report.bounds, europe_bounds);
    assert_eq!(report.zooms, ZoomRange::new(10, 14).expect("valid"));
    assert_eq!(report.tile_count, 4568);
    assert_eq!(report.levels.len(), 5);
    assert_eq!(
        report.levels[0],
        ZoomLevelReport {
            zoom: 10,
            x_min: 551,
            x_max: 554,
            y_min: 342,
            y_max: 347,
            tile_count: 24
        }
    );
    assert_eq!(
        report
            .levels
            .iter()
            .map(|level| level.tile_count)
            .sum::<u64>(),
        report.tile_count
    );
}

/// Pins the key names, because they are the wire contract: the Python client
/// reads `tile_count`/`levels`, and the Node client reads `bounds`/`zooms` as
/// objects. A rename here is a break in two languages, so it fails here first.
#[rstest]
fn a_report_serialises_under_the_wire_key_names(europe_bounds: Extent) {
    let plan =
        TilePlan::new(europe_bounds, ZoomRange::parse("10-14").expect("valid")).expect("valid");

    let value = serde_json::to_value(plan.report()).expect("serialises");

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
    assert_eq!(value["zooms"], serde_json::json!({"min": 10, "max": 14}));
    assert_eq!(value["bounds"]["min_x"], serde_json::json!(14.0));
}

proptest! {
    #[test]
    fn a_full_world_level_iterates_exactly_its_reported_count(zoom in 0u32..=6) {
        let world = Extent::new(-180.0, -MAX_LATITUDE, 180.0, MAX_LATITUDE);
        let plan = TilePlan::new(world, ZoomRange::new(zoom, zoom).expect("bounded zoom"))
            .expect("world extent is valid");

        prop_assert_eq!(plan.iter().count() as u64, plan.level(zoom).tile_count());
    }

    #[test]
    fn zoom_range_count_matches_its_inclusive_levels(
        first in 0u32..=MAX_ZOOM,
        second in 0u32..=MAX_ZOOM,
    ) {
        let (min, max) = if first <= second {
            (first, second)
        } else {
            (second, first)
        };
        let range = ZoomRange::new(min, max).expect("ordered bounded range");

        prop_assert_eq!(range.count(), max - min + 1);
        prop_assert_eq!(range.iter().count() as u32, range.count());
    }
}
