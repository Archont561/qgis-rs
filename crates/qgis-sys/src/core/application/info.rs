#[cxx::bridge(namespace = "qgis_shim::core")]
pub mod ffi {
    #[derive(Debug)]
    pub struct AppInfo {
        pub version: String,
        pub qt_version: String,
        pub platform: String,
    }

    unsafe extern "C++" {
        include!("qgis-sys/include/core/application_info.h");
        fn application_info() -> AppInfo;
    }
}
