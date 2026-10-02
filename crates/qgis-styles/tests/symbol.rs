//! Symbols: the three kinds, and what they serialise to.

use qgis_styles::*;

#[test]
fn creates_symbols() {
    let red = Rgba::new(255, 0, 0);
    let marker = Symbol::marker(red, 8.0);
    assert!(matches!(marker, Symbol::Marker(_)));

    let line = Symbol::line(red, 2.0);
    assert!(matches!(line, Symbol::Line(_)));
}

#[test]
fn serializes_symbols() {
    let sym = Symbol::fill(Rgba::new(0, 255, 0));
    let json = serde_json::to_string(&sym).unwrap();
    assert!(json.contains("fill"));
}
