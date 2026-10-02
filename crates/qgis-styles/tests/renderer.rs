//! Renderer validation: a renderer that claims a field or a class set must
//! actually carry one.

use qgis_styles::color::Rgba;
use qgis_styles::*;

#[test]
fn validates_renderer() {
    let sym = Symbol::fill(Rgba::new(255, 0, 0));
    let single = Renderer::single(sym);
    assert!(single.is_valid());

    let empty_cat = Renderer::Categorized {
        attr: "type".to_string(),
        categories: vec![],
        default_symbol: None,
    };
    assert!(!empty_cat.is_valid());
}
