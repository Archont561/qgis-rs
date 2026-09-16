use qgis_sys::application_info_ffi as info_ffi;

#[test]
fn version_not_empty() {
    let info = info_ffi::application_info();
    assert!(!info.version.is_empty());
}

#[test]
fn version_has_dot() {
    let info = info_ffi::application_info();
    assert!(info.version.contains('.'));
}

#[test]
fn qt_version_not_empty() {
    let info = info_ffi::application_info();
    assert!(!info.qt_version.is_empty());
}

#[test]
fn platform_not_empty() {
    let info = info_ffi::application_info();
    assert!(!info.platform.is_empty());
}

#[test]
fn print_info() {
    let info = info_ffi::application_info();
    println!(
        "\nqgis={}  qt={}  os={}",
        info.version, info.qt_version, info.platform
    );
}
