//! Hex colour parsing, and what counts as malformed.

use qgis_styles::*;
use rstest::rstest;

#[test]
fn parses_hex_colors() {
    let red = Rgba::from_hex("#ff0000").unwrap();
    assert_eq!(red, Rgba::new(255, 0, 0));
    assert_eq!(red.to_hex(), "#ff0000");

    let with_alpha = Rgba::from_hex("#ff000080").unwrap();
    assert_eq!(with_alpha.a, 128);
}

#[rstest]
#[case::not_hexadecimal("#xyz")]
#[case::odd_length("#12345")]
fn rejects_invalid_hex(#[case] text: &str) {
    assert!(Rgba::from_hex(text).is_err(), "{text:?} should fail");
}
