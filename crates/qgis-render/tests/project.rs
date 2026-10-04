//! Opening `.qgs` and `.qgz` projects, rejecting everything else, and the
//! explicit backend boundary of the pure Rust project reader.
//!
//! Every test here needs the same thing: a scratch directory with a project
//! file in it, removed afterwards. That was three hand-rolled copies of
//! create/write/remove with a hard-coded directory name each; it is now one
//! `scratch` fixture whose `Drop` does the cleanup even when an assertion
//! fails, and whose name is unique per test rather than shared.

use std::path::{Path, PathBuf};

use qgis_render::*;
use rstest::{fixture, rstest};

/// A scratch directory that removes itself.
///
/// Unique per instance: the previous fixed names meant two tests in different
/// processes could delete each other's directory mid-run.
struct Scratch {
    path: PathBuf,
}

impl Scratch {
    fn new() -> Self {
        let unique = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("system clock is after the epoch")
            .as_nanos();
        let path = std::env::temp_dir().join(format!("qgis-render-project-{unique}"));
        std::fs::create_dir_all(&path).expect("create scratch dir");
        Self { path }
    }

    fn path(&self) -> &Path {
        &self.path
    }

    /// Write a minimal project file and return its path.
    fn project(&self, name: &str) -> PathBuf {
        let path = self.path.join(name);
        std::fs::write(&path, b"<qgis></qgis>").expect("write");
        path
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.path).ok();
    }
}

#[fixture]
fn scratch() -> Scratch {
    Scratch::new()
}

#[rstest]
fn opens_qgs_and_qgz_projects(scratch: Scratch) {
    let qgs = Project::open(scratch.project("map.qgs")).expect("open .qgs");
    assert_eq!(qgs.format(), ProjectFormat::Qgs);

    let qgz = Project::open(scratch.project("map.qgz")).expect("open .qgz");
    assert_eq!(qgz.format(), ProjectFormat::Qgz);

    let info = qgs.info().expect("info");
    assert!(info.size_bytes > 0);
    assert!(info.note.is_some());
    assert!(info.crs.is_none());
}

#[rstest]
fn rejects_missing_files_and_other_extensions(scratch: Scratch) {
    assert!(matches!(
        Project::open("/definitely/not/here.qgs"),
        Err(Error::ProjectNotFound { .. })
    ));

    let text = scratch.project("notes.txt");
    assert!(matches!(
        Project::open(&text),
        Err(Error::UnsupportedProject { .. })
    ));
}

#[rstest]
fn pure_project_reader_reports_native_operations_as_backend_gated(scratch: Scratch) {
    let project = Project::open(scratch.project("map.qgs")).expect("open");

    let error = project.layers().expect_err("no backend");
    assert!(matches!(error, Error::Unimplemented { .. }));
    assert!(error.to_string().contains("QGIS backend"));

    let settings = RenderSettings::new(scratch.path().join("out.png")).expect("png output");
    assert!(project.render(&settings).is_err());
    assert!(project.export_layer("buildings", "geojson").is_err());
}

#[rstest]
#[case("QGS", Some(ProjectFormat::Qgs))]
#[case("qgz", Some(ProjectFormat::Qgz))]
#[case("png", None)]
fn infers_formats_from_extensions(
    #[case] extension: &str,
    #[case] expected: Option<ProjectFormat>,
) {
    assert_eq!(ProjectFormat::from_extension(extension), expected);
}

#[test]
fn a_format_names_its_own_extension() {
    assert_eq!(ProjectFormat::Qgs.extension(), "qgs");
}
