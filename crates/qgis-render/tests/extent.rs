//! Extents: the `minx,miny,maxx,maxy` text a user types, the `Display` form it
//! round-trips to, and the two ways an extent can be invalid.

use qgis_render::*;

#[test]
fn parses_the_cli_form() {
    let extent = Extent::parse("14, 50, 15, 51").expect("valid extent");
    assert_eq!(extent, Extent::new(14.0, 50.0, 15.0, 51.0));
    assert_eq!(extent.width(), 1.0);
    assert_eq!(extent.height(), 1.0);
    assert!(extent.contains(14.5, 50.5));
    assert!(!extent.contains(13.0, 50.5));
}

#[test]
fn round_trips_through_display() {
    let extent = Extent::new(14.0, 50.0, 15.0, 51.0);
    assert_eq!(
        Extent::parse(&extent.to_string()).expect("round trip"),
        extent
    );
}

#[test]
fn rejects_incomplete_and_reversed_extents() {
    for text in ["14,50,15", "a,b,c,d", "15,50,14,51", ""] {
        assert!(Extent::parse(text).is_err(), "{text:?} should not parse");
    }
}

#[test]
fn detects_overlap() {
    let a = Extent::new(0.0, 0.0, 10.0, 10.0);
    assert!(a.intersects(&Extent::new(5.0, 5.0, 20.0, 20.0)));
    assert!(!a.intersects(&Extent::new(20.0, 20.0, 30.0, 30.0)));
}
