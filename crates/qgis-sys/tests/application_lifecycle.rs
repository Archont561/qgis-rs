mod helpers;

use qgis_sys::application_info_ffi as info_ffi;

#[test]
fn lifecycle_and_info() {
    let _app = helpers::AppHandle::new();

    let info = info_ffi::application_info();
    println!(
        "qgis={}  qt={}  os={}",
        info.version, info.qt_version, info.platform
    );

    assert!(!info.version.is_empty());
    assert!(info.version.contains('.'));
    assert!(!info.qt_version.is_empty());
    assert!(!info.platform.is_empty());
}
