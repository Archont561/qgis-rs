//! Extents: the `minx,miny,maxx,maxy` text a user types, the `Display` form it
//! round-trips to, and the two ways an extent can be invalid.

use proptest::prelude::*;
use qgis_render::*;
use rstest::rstest;

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

#[rstest]
#[case::too_few_edges("14,50,15")]
#[case::not_numbers("a,b,c,d")]
#[case::reversed("15,50,14,51")]
#[case::empty("")]
fn rejects_incomplete_and_reversed_extents(#[case] text: &str) {
    assert!(Extent::parse(text).is_err(), "{text:?} should not parse");
}

#[test]
fn detects_overlap() {
    let a = Extent::new(0.0, 0.0, 10.0, 10.0);
    assert!(a.intersects(&Extent::new(5.0, 5.0, 20.0, 20.0)));
    assert!(!a.intersects(&Extent::new(20.0, 20.0, 30.0, 30.0)));
}

proptest! {
    #[test]
    fn finite_extents_round_trip_through_display(
        first_x in -1_000_000.0f64..1_000_000.0,
        second_x in -1_000_000.0f64..1_000_000.0,
        first_y in -1_000_000.0f64..1_000_000.0,
        second_y in -1_000_000.0f64..1_000_000.0,
    ) {
        let (min_x, max_x) = if first_x <= second_x {
            (first_x, second_x)
        } else {
            (second_x, first_x)
        };
        let (min_y, max_y) = if first_y <= second_y {
            (first_y, second_y)
        } else {
            (second_y, first_y)
        };
        let extent = Extent::new(min_x, min_y, max_x, max_y);

        prop_assert_eq!(
            Extent::parse(&extent.to_string()).expect("display is parseable"),
            extent
        );
    }

    #[test]
    fn intersection_is_symmetric(
        first_x in -1_000.0f64..1_000.0,
        second_x in -1_000.0f64..1_000.0,
        first_y in -1_000.0f64..1_000.0,
        second_y in -1_000.0f64..1_000.0,
        other_x in -1_000.0f64..1_000.0,
        other_width in 0.0f64..1_000.0,
        other_y in -1_000.0f64..1_000.0,
        other_height in 0.0f64..1_000.0,
    ) {
        let (min_x, max_x) = if first_x <= second_x {
            (first_x, second_x)
        } else {
            (second_x, first_x)
        };
        let (min_y, max_y) = if first_y <= second_y {
            (first_y, second_y)
        } else {
            (second_y, first_y)
        };
        let a = Extent::new(min_x, min_y, max_x, max_y);
        let b = Extent::new(
            other_x,
            other_y,
            other_x + other_width,
            other_y + other_height,
        );

        prop_assert_eq!(a.intersects(&b), b.intersects(&a));
    }
}
