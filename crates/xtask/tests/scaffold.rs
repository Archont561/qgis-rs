//! The scaffolder's templates name each other consistently — a mismatch is a
//! build failure in a generated file that does not say why — and wiring a new
//! module into a `mod.rs` twice leaves one line, not two.

use std::fs;
use xtask::scaffold::{append_once, bridge_source, header_source, shim_source};

#[test]
fn the_generated_files_name_each_other_consistently() {
    let header = header_source("core", "geometry", "geometry", "QgsGeometryHandle");
    let bridge = bridge_source("core", "geometry", "QgsGeometryHandle");
    let shim = shim_source("core", "geometry", "QgsGeometry", "QgsGeometryHandle");

    // The cxx bridge includes the header, and the header includes the
    // bridge's generated counterpart — a mismatch here is a build failure
    // in a place that does not name the cause.
    assert!(header.contains("qgis-sys/src/core/geometry/geometry.rs.h"));
    assert!(bridge.contains("include!(\"qgis-sys/include/core/geometry.h\")"));
    assert!(shim.contains("#include \"qgis-sys/include/core/geometry.h\""));
    assert!(shim.contains("::QgsGeometry"));
    assert!(bridge.contains("type QgsGeometryHandle;"));
}

#[test]
fn appending_a_module_line_is_idempotent() {
    let directory = std::env::temp_dir().join("qgis-xtask-scaffold-append");
    fs::create_dir_all(&directory).expect("create dir");
    let path = directory.join("mod.rs");
    fs::write(&path, "pub mod application;\n").expect("seed");

    append_once(&path, "pub mod geometry;", "pub mod geometry;\n").expect("first append");
    append_once(&path, "pub mod geometry;", "pub mod geometry;\n").expect("second append");

    let contents = fs::read_to_string(&path).expect("read back");
    assert_eq!(contents.matches("pub mod geometry;").count(), 1);
}
