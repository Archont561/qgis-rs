//! Render settings: the format inferred from an output path, the builder
//! chain that accumulates options, and the MIME type each format claims.

use qgis_render::*;
use rstest::rstest;

#[test]
fn infers_the_format_from_the_output_path() {
    for (name, format) in [
        ("map.png", ImageFormat::Png),
        ("map.JPG", ImageFormat::Jpeg),
        ("map.webp", ImageFormat::WebP),
        ("map.svg", ImageFormat::Svg),
        ("map.pdf", ImageFormat::Pdf),
    ] {
        let settings = RenderSettings::new(name).expect("known format");
        assert_eq!(settings.format, format, "{name}");
        assert_eq!(settings.width, 1024);
        assert_eq!(settings.height, 768);
        assert_eq!(settings.dpi, 96.0);
    }
    assert!(RenderSettings::new("map.bmp").is_err());
    assert!(RenderSettings::new("map").is_err());
}

#[test]
fn builders_accumulate() {
    let settings = RenderSettings::new("out.png")
        .expect("png")
        .with_size(2048, 1536)
        .with_dpi(300.0)
        .with_crs(Crs::web_mercator())
        .with_extent(Extent::new(14.0, 50.0, 15.0, 51.0))
        .with_layers(["buildings".to_string(), "roads".to_string()])
        .with_layout("A4 Landscape");

    assert_eq!((settings.width, settings.height), (2048, 1536));
    assert_eq!(settings.dpi, 300.0);
    assert_eq!(settings.crs, Some(Crs::web_mercator()));
    assert_eq!(settings.layers, vec!["buildings", "roads"]);
    assert_eq!(settings.layout.as_deref(), Some("A4 Landscape"));
}

#[rstest]
#[case(ImageFormat::Png, "image/png", true)]
#[case(ImageFormat::Svg, "image/svg+xml", false)]
#[case(ImageFormat::Pdf, "application/pdf", false)]
fn formats_know_their_mime_types(
    #[case] format: ImageFormat,
    #[case] mime_type: &str,
    #[case] is_raster: bool,
) {
    assert_eq!(format.mime_type(), mime_type);
    assert_eq!(format.is_raster(), is_raster);
}
