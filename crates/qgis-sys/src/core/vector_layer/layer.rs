#[cxx::bridge(namespace = "qgis_shim::core")]
pub mod ffi {
    unsafe extern "C++" {
        include!("qgis-sys/include/core/vector_layer.h");

        type QgsVectorLayerHandle;

        fn vector_layer_new(
            uri: &str,
            name: &str,
            provider: &str,
        ) -> UniquePtr<QgsVectorLayerHandle>;

        fn vector_layer_is_valid(handle: &QgsVectorLayerHandle) -> bool;
        fn vector_layer_name(handle: &QgsVectorLayerHandle) -> String;
        fn vector_layer_feature_count(handle: &QgsVectorLayerHandle) -> i64;
        fn vector_layer_crs_authid(handle: &QgsVectorLayerHandle) -> String;
        fn vector_layer_geometry_type_name(handle: &QgsVectorLayerHandle) -> String;
    }
}
