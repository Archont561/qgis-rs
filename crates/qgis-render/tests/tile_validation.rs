//! Checked bounds reject unsafe indices before tile arithmetic.
use qgis_render::Tile;

#[test]
fn checked_bounds_preserve_known_tile_geometry() {
    let bounds = Tile::new(10, 551, 342)
        .checked_bounds()
        .expect("valid tile");
    assert_eq!(bounds.min_x, 13.710_937_5);
    assert_eq!(bounds.max_x, 14.0625);
    assert!((bounds.max_y - 51.179_342_979_289_27).abs() < 1e-12);
    assert!(Tile::new(0, 0, 0).checked_bounds().is_some());
    assert!(Tile::new(22, 4_194_303, 4_194_303)
        .checked_bounds()
        .is_some());
}

#[test]
fn checked_bounds_reject_invalid_zoom_and_indices_without_overflow_or_clamping() {
    for tile in [
        Tile::new(0, 1, 0),
        Tile::new(0, 0, 1),
        Tile::new(22, 4_194_304, 0),
        Tile::new(22, 0, 4_194_304),
        Tile::new(23, 0, 0),
        Tile::new(32, 0, 0),
        Tile::new(u32::MAX, 0, 0),
        Tile::new(10, u32::MAX, u32::MAX),
    ] {
        assert!(tile.checked_bounds().is_none(), "{tile:?}");
    }
}
