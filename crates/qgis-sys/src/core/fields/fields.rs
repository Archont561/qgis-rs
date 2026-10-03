#[cxx::bridge(namespace = "qgis_shim::core")]
pub mod ffi {
    unsafe extern "C++" {
        include!("qgis-sys/include/core/fields.h");

        type QgsFieldsHandle;

        fn fields_new_empty() -> UniquePtr<QgsFieldsHandle>;
        fn fields_count(handle: &QgsFieldsHandle) -> i64;
        fn fields_name(handle: &QgsFieldsHandle, index: i64) -> String;
        fn fields_type(handle: &QgsFieldsHandle, index: i64) -> String;
        fn fields_precision(handle: &QgsFieldsHandle, index: i64) -> i64;
    }
}
