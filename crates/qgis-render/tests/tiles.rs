//! Tile arithmetic — the part of this repository with exact, checkable
//! answers. The pyramid over `14,50,15,51` at z10-14 is 4568 tiles, and the
//! same numbers are asserted again from Python and from JavaScript.

use qgis_render::*;

/// Central Europe: the bounds the CLI docs use.
fn bounds() -> Extent {
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

#[test]
fn plans_a_single_zoom_level() {
    let plan = TilePlan::new(bounds(), ZoomRange::parse("10").expect("valid")).expect("valid");
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

#[test]
fn plans_a_zoom_range() {
    let plan = TilePlan::new(bounds(), ZoomRange::parse("10-14").expect("valid")).expect("valid");
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
