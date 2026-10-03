//! Stylesheets: building one, round-tripping it through JSON, and the
//! MapLibre translation.

use qgis_styles::color::Rgba;
use qgis_styles::symbol::Symbol;
use qgis_styles::*;

#[test]
fn creates_stylesheet() {
    let sym = Symbol::fill(Rgba::new(255, 0, 0));
    let renderer = Renderer::single(sym);
    let style = LayerStyle::new(renderer).with_opacity(0.8);
    assert!(style.is_valid());

    let sheet = StyleSheet::new().with_layer("buildings", style);
    assert_eq!(sheet.layers.len(), 1);
    assert!(sheet.is_valid());
}

#[test]
fn round_trips_json() {
    let sym = Symbol::fill(Rgba::new(0, 255, 0));
    let sheet = StyleSheet::new().with_layer("roads", LayerStyle::new(Renderer::single(sym)));
    let json = sheet.to_json().unwrap();
    let parsed = StyleSheet::from_json(&json).unwrap();
    assert_eq!(parsed.layers.len(), 1);
}

#[test]
fn converts_to_maplibre() {
    let sym = Symbol::fill(Rgba::new(0, 0, 255));
    let sheet = StyleSheet::new().with_layer("water", LayerStyle::new(Renderer::single(sym)));
    let ml = sheet.to_maplibre();
    assert_eq!(ml["version"], 8);
}
