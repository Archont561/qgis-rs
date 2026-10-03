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
        let format =
            ProjectFormat::from_extension(extension).ok_or_else(|| Error::UnsupportedProject {
                path: path.to_path_buf(),
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
                "CRS, layer count and extent are only available through the native QGIS project reader"
                    .to_string(),
            ),
        })
    }

    /// List the project's layers.
    ///
    /// # Errors
    ///
    /// This backend-agnostic reader does not load QGIS project layers. Use the
    /// transport-level native manager operation when the QGIS feature is enabled.
    pub fn layers(&self) -> Result<Vec<LayerSummary>> {
        Err(Error::Unimplemented {
            feature: "listing project layers",
        })
    }

    /// Render the project to an image.
    ///
    /// # Errors
    ///
    /// This backend-agnostic reader does not render through QGIS. Use the
    /// transport-level `render_map` operation for native rendering.
    pub fn render(&self, _settings: &RenderSettings) -> Result<RenderedMap> {
        Err(Error::Unimplemented {
            feature: "rendering a project",
        })
    }

    /// Export a layer's features.
    ///
    /// # Errors
    ///
    /// This backend-agnostic reader does not export through QGIS. Use the
    /// transport-level `export_features` operation for native export.
    pub fn export_layer(&self, _layer: &str, _format: &str) -> Result<PathBuf> {
        Err(Error::Unimplemented {
            feature: "exporting features",
        })
    }
}
