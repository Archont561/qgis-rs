//! QGIS projects: opening them and describing them.

use std::path::{Path, PathBuf};

use crate::crs::Crs;
use crate::error::{Error, Result};
use crate::extent::Extent;
use crate::render::{RenderSettings, RenderedMap};

/// The on-disk form of a QGIS project.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ProjectFormat {
    /// `.qgs` — plain XML.
    Qgs,
    /// `.qgz` — zipped XML bundle.
    Qgz,
}

impl ProjectFormat {
    /// Infer the format from a file extension.
    #[must_use]
    pub fn from_extension(extension: &str) -> Option<Self> {
        match extension.to_ascii_lowercase().as_str() {
            "qgs" => Some(Self::Qgs),
            "qgz" => Some(Self::Qgz),
            _ => None,
        }
    }

    /// The canonical file extension, without the dot.
    #[must_use]
    pub const fn extension(&self) -> &'static str {
        match self {
            Self::Qgs => "qgs",
            Self::Qgz => "qgz",
        }
    }
}

/// What qgis-rs can say about a project.
///
/// The optional fields need `libqgis_core`; they stay `None` until the QGIS
/// backend is wired up, and `note` explains that to whoever asked.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct ProjectInfo {
    /// Where the project lives.
    pub path: PathBuf,
    /// Whether it is a `.qgs` or a `.qgz`.
    pub format: ProjectFormat,
    /// Size on disk, in bytes.
    pub size_bytes: u64,
    /// Project CRS.
    pub crs: Option<Crs>,
    /// Number of layers in the project.
    pub layer_count: Option<usize>,
    /// Full extent of all layers.
    pub extent: Option<Extent>,
    /// Why some fields are missing.
    pub note: Option<String>,
}

/// A layer inside a project.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct LayerSummary {
    /// Layer name as shown in the QGIS layer tree.
    pub name: String,
    /// Data provider key, e.g. `ogr` or `postgres`.
    pub provider: String,
    /// Layer CRS.
    pub crs: Option<Crs>,
    /// Feature count, when the provider reports one.
    pub feature_count: Option<i64>,
    /// Geometry type name, e.g. `Polygon`.
    pub geometry_type: Option<String>,
}

/// A QGIS project on disk.
#[derive(Debug, Clone, PartialEq)]
pub struct Project {
    path: PathBuf,
    format: ProjectFormat,
}

impl Project {
    /// Open a project file.
    ///
    /// Opening only inspects the path: nothing is parsed yet, so this is cheap
    /// and works without QGIS.
    ///
    /// # Errors
    ///
    /// Returns [`Error::ProjectNotFound`] when the file is missing and
    /// [`Error::UnsupportedProject`] when it is neither `.qgs` nor `.qgz`.
    pub fn open(path: impl AsRef<Path>) -> Result<Self> {
        let path = path.as_ref();
        if !path.exists() {
            return Err(Error::ProjectNotFound {
                path: path.to_path_buf(),
            });
        }
        let extension = path
            .extension()
            .and_then(|extension| extension.to_str())
            .unwrap_or_default();
        let format = ProjectFormat::from_extension(extension).ok_or_else(|| {
            Error::UnsupportedProject {
                path: path.to_path_buf(),
            }
        })?;
        Ok(Self {
            path: path.to_path_buf(),
            format,
        })
    }

    /// The path the project was opened from.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Whether the project is a `.qgs` or a `.qgz`.
    #[must_use]
    pub const fn format(&self) -> ProjectFormat {
        self.format
    }

    /// Describe the project.
    ///
    /// # Errors
    ///
    /// Returns [`Error::Io`] when the file cannot be stat'ed.
    pub fn info(&self) -> Result<ProjectInfo> {
        let metadata = std::fs::metadata(&self.path)?;
        Ok(ProjectInfo {
            path: self.path.clone(),
            format: self.format,
            size_bytes: metadata.len(),
            crs: None,
            layer_count: None,
            extent: None,
            note: Some(
                "CRS, layer count and extent need the QGIS backend, which is not wired up yet"
                    .to_string(),
            ),
        })
    }

    /// List the project's layers.
    ///
    /// # Errors
    ///
    /// Always [`Error::Unimplemented`] until the QGIS backend lands.
    pub fn layers(&self) -> Result<Vec<LayerSummary>> {
        Err(Error::Unimplemented {
            feature: "listing project layers",
        })
    }

    /// Render the project to an image.
    ///
    /// # Errors
    ///
    /// Always [`Error::Unimplemented`] until the QGIS backend lands.
    pub fn render(&self, _settings: &RenderSettings) -> Result<RenderedMap> {
        Err(Error::Unimplemented {
            feature: "rendering a project",
        })
    }

    /// Export a layer's features.
    ///
    /// # Errors
    ///
    /// Always [`Error::Unimplemented`] until the QGIS backend lands.
    pub fn export_layer(&self, _layer: &str, _format: &str) -> Result<PathBuf> {
        Err(Error::Unimplemented {
            feature: "exporting features",
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
    fn qgis_backed_operations_report_themselves_as_unwired() {
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
        assert_eq!(ProjectFormat::from_extension("QGS"), Some(ProjectFormat::Qgs));
        assert_eq!(ProjectFormat::from_extension("qgz"), Some(ProjectFormat::Qgz));
        assert_eq!(ProjectFormat::from_extension("png"), None);
        assert_eq!(ProjectFormat::Qgs.extension(), "qgs");
    }
}
