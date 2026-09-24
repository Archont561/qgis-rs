use std::cell::RefCell;

use qgis_sys::application_ffi as app_ffi;

thread_local! {
    static APP: RefCell<Option<cxx::UniquePtr<app_ffi::QgsApplication>>> =
        const { RefCell::new(None) };
}

/// Process-wide handle to the thread's one-and-only QGIS application.
///
/// QGIS/Qt support exactly one `QApplication` per process, so the helper
/// initializes a single app on first use (creating it fresh would corrupt the
/// heap on the second `QApplication`) and keeps it alive until the test binary
/// exits. The test harness runs sequentially on one thread (`--test-threads=1`),
/// so a `thread_local` is sufficient.
pub struct AppHandle(());

impl AppHandle {
    pub fn new() -> Self {
        APP.with(|cell| {
            let mut cell = cell.borrow_mut();
            if cell.is_none() {
                let prefix = std::env::var("CONDA_PREFIX").unwrap_or_default();
                let mut inner = app_ffi::application_new(&prefix);
                assert!(!inner.is_null(), "application_new returned null");
                app_ffi::application_init_qgis(inner.pin_mut());
                *cell = Some(inner);
            }
        });
        AppHandle(())
    }
}
