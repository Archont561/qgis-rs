//! Opening `.qgs` and `.qgz` projects, rejecting everything else, and the
//! explicit backend boundary of the pure Rust project reader.

use std::path::{Path, PathBuf};

use qgis_render::*;

fn write_project(dir: &Path, name: &str) -> PathBuf {
    let path = dir.join(name);
    std::fs::write(&path, b"<qgis></qgis>").expect("write");
    path
}

#[test]
fn opens_qgs_and_qgz_projects() {
    let dir = std::env::temp_dir().join("qgis-render-project-format");
    std::fs::create_dir_all(&dir).expect("create dir");

    let qgs = Project::open(write_project(&dir, "map.qgs")).expect("open .qgs");
    assert_eq!(qgs.format(), ProjectFormat::Qgs);

    let qgz = Project::open(write_project(&dir, "map.qgz")).expect("open .qgz");
    assert_eq!(qgz.format(), ProjectFormat::Qgz);

    let info = qgs.info().expect("info");
    assert!(info.size_bytes > 0);
    assert!(info.note.is_some());
    assert!(info.crs.is_none());

    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn rejects_missing_files_and_other_extensions() {
    assert!(matches!(
        Project::open("/definitely/not/here.qgs"),
        Err(Error::ProjectNotFound { .. })
    ));

    let dir = std::env::temp_dir().join("qgis-render-project-extension");
    std::fs::create_dir_all(&dir).expect("create dir");
    let text = write_project(&dir, "notes.txt");
    assert!(matches!(
        Project::open(&text),
        Err(Error::UnsupportedProject { .. })
    ));
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn pure_project_reader_reports_native_operations_as_backend_gated() {
    let dir = std::env::temp_dir().join("qgis-render-project-unwired");
    std::fs::create_dir_all(&dir).expect("create dir");
    let project = Project::open(write_project(&dir, "map.qgs")).expect("open");

    let error = project.layers().expect_err("no backend");
    assert!(matches!(error, Error::Unimplemented { .. }));
    assert!(error.to_string().contains("QGIS backend"));

    let settings = RenderSettings::new(dir.join("out.png")).expect("png output");
    assert!(project.render(&settings).is_err());
    assert!(project.export_layer("buildings", "geojson").is_err());

    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn infers_formats_from_extensions() {
    assert_eq!(
        ProjectFormat::from_extension("QGS"),
        Some(ProjectFormat::Qgs)
    );
    assert_eq!(
        ProjectFormat::from_extension("qgz"),
        Some(ProjectFormat::Qgz)
    );
    assert_eq!(ProjectFormat::from_extension("png"), None);
    assert_eq!(ProjectFormat::Qgs.extension(), "qgs");
}
