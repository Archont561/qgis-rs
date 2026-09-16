#[cxx::bridge(namespace = "qgis_shim::core")]
pub mod ffi {
    unsafe extern "C++" {
        include!("qgis-sys/include/core/application.h");

        type QgsApplication;

        fn application_new(prefix_path: &str) -> UniquePtr<QgsApplication>;
        fn application_init_qgis(app: Pin<&mut QgsApplication>);
        fn application_exit_qgis(app: Pin<&mut QgsApplication>);
    }
}
