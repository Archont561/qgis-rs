//! Hex colour parsing, and what counts as malformed.

use qgis_styles::*;

#[test]
fn parses_hex_colors() {
    let red = Rgba::from_hex("#ff0000").unwrap();
    assert_eq!(red, Rgba::new(255, 0, 0));
    assert_eq!(red.to_hex(), "#ff0000");

    let with_alpha = Rgba::from_hex("#ff000080").unwrap();
    assert_eq!(with_alpha.a, 128);
}

#[test]
fn rejects_invalid_hex() {
    assert!(Rgba::from_hex("#xyz").is_err());
    assert!(Rgba::from_hex("#12345").is_err());
}
