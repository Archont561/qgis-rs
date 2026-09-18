use qgis_sys::application_ffi as app_ffi;

pub struct AppHandle {
    inner: cxx::UniquePtr<app_ffi::QgsApplication>,
}

impl AppHandle {
    pub fn new() -> Self {
        let prefix = std::env::var("CONDA_PREFIX").unwrap_or_default();
        let mut inner = app_ffi::application_new(&prefix);
        assert!(!inner.is_null(), "application_new returned null");
        app_ffi::application_init_qgis(inner.pin_mut());
        Self { inner }
    }
}

impl Drop for AppHandle {
    fn drop(&mut self) {
        if !self.inner.is_null() {
            app_ffi::application_exit_qgis(self.inner.pin_mut());
        }
    }
}
