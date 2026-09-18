mod helpers;

use qgis_sys::vector_layer_ffi as layer_ffi;

fn test_data_path() -> String {
    format!(
        "{}/tests/fixtures/points.gpkg",
        env!("CARGO_MANIFEST_DIR")
    )
}

fn open_test_layer() -> cxx::UniquePtr<layer_ffi::QgsVectorLayerHandle> {
    let path = test_data_path();
    let layer = layer_ffi::vector_layer_new(&path, "points", "ogr");
    assert!(!layer.is_null(), "vector_layer_new returned null");
    layer
}

#[test]
fn layer_is_valid() {
    let _app = helpers::AppHandle::new();
    let layer = open_test_layer();
    assert!(layer_ffi::vector_layer_is_valid(&layer));
}

#[test]
fn layer_name() {
    let _app = helpers::AppHandle::new();
    let layer = open_test_layer();
    assert_eq!(layer_ffi::vector_layer_name(&layer), "points");
}

#[test]
fn layer_feature_count() {
    let _app = helpers::AppHandle::new();
    let layer = open_test_layer();
    assert_eq!(layer_ffi::vector_layer_feature_count(&layer), 3);
}

#[test]
fn layer_crs() {
    let _app = helpers::AppHandle::new();
    let layer = open_test_layer();
    assert_eq!(
        layer_ffi::vector_layer_crs_authid(&layer),
        "EPSG:4326"
    );
}

#[test]
fn layer_geometry_type() {
    let _app = helpers::AppHandle::new();
    let layer = open_test_layer();
    let geom = layer_ffi::vector_layer_geometry_type_name(&layer);
    assert!(
        geom.contains("Point"),
        "expected Point, got: {}",
        geom
    );
}
