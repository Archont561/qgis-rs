//! Error types for the rendering engine.

use std::path::PathBuf;

/// Everything that can go wrong inside `qgis-render`.
///
/// The engine is backend-agnostic: operations that need `libqgis_core` report
/// [`Error::Unimplemented`] until the QGIS backend is wired up, which keeps the
/// pure-Rust parts (extents, CRS, tile pyramids) usable everywhere.
#[derive(Debug, thiserror::Error)]
pub enum Error {
    /// A file or directory could not be read or written.
    #[error("I/O error: {source}")]
    Io {
        #[source]
        source: std::io::Error,
    },

    /// The project file does not exist.
    #[error("project not found: {}", path.display())]
    ProjectNotFound { path: PathBuf },

    /// The file exists but is neither `.qgs` nor `.qgz`.
    #[error("not a QGIS project: {}", path.display())]
    UnsupportedProject { path: PathBuf },

    /// A string could not be read as `minx,miny,maxx,maxy`.
    #[error("invalid extent {value:?}: expected \"minx,miny,maxx,maxy\"")]
    InvalidExtent { value: String },

    /// A string could not be read as a zoom level or `min-max` range.
    #[error("invalid zoom range {value:?}: expected \"12\" or \"10-14\"")]
    InvalidZoomRange { value: String },

    /// The authority code is not shaped like `EPSG:3857`.
    #[error("unknown coordinate reference system: {auth_id:?}")]
    UnknownCrs { auth_id: String },

    /// An output path has no recognisable image-format extension.
    #[error("cannot infer an image format from {}", path.display())]
    UnknownImageFormat { path: PathBuf },

    /// The operation needs the QGIS backend, which is not wired up yet.
    #[error("{feature} needs the QGIS backend, which is not wired up yet")]
    Unimplemented { feature: &'static str },
}

/// Convenience alias used across the crate.
pub type Result<T, E = Error> = std::result::Result<T, E>;

impl From<std::io::Error> for Error {
    fn from(source: std::io::Error) -> Self {
        Self::Io { source }
    }
}
