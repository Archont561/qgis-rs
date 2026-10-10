//! The meta crate re-exports exactly the engines whose features are enabled.
//! Each test is compiled only under its feature, so the feature matrix is the
//! thing under test: `cargo test -p qgis-rs --no-default-features --features X`.

#[cfg(feature = "render")]
#[test]
fn render_is_the_same_engine_under_its_short_name() {
    assert_eq!(
        qgis_rs::render::crs::Crs::wgs84().auth_id(),
        qgis_render::crs::Crs::wgs84().auth_id()
    );
}

#[cfg(feature = "server")]
#[test]
fn server_exposes_its_configuration_type() {
    assert!(std::mem::size_of::<qgis_rs::server::ServerConfig>() > 0);
}

#[cfg(feature = "styles")]
#[test]
fn styles_exposes_its_color_type() {
    assert_eq!(std::mem::size_of::<qgis_rs::styles::color::Rgba>(), 4);
}

#[cfg(feature = "cli")]
#[test]
fn cli_exposes_its_command_tree() {
    assert!(std::mem::size_of::<qgis_rs::cli::Cli>() > 0);
}

#[cfg(not(feature = "render"))]
#[test]
fn without_render_the_facade_still_builds() {
    // Compiling this file is the assertion: no engine is re-exported.
}
