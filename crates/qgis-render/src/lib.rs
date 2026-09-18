//! The qgis-rs rendering engine.
//!
//! `qgis-render` is the library every other qgis-rs component is built on: the
//! CLI, the HTTP server and the MCP server all take their types from here.
//! It is deliberately backend-agnostic — the geometry that does not need QGIS
//! (extents, CRS codes, XYZ tile pyramids) is implemented in pure Rust, while
//! the operations that do need `libqgis_core` return
//! [`Error::Unimplemented`] until the QGIS backend is wired up.
//!
//! ```
//! use qgis_render::{Extent, TilePlan, ZoomRange};
//!
//! let bounds = Extent::parse("14,50,15,51")?;
//! let plan = TilePlan::new(bounds, ZoomRange::parse("10-14")?)?;
//! assert_eq!(plan.tile_count(), 4568);
//! # Ok::<(), qgis_render::Error>(())
//! ```

pub mod crs;
pub mod error;
pub mod extent;
pub mod project;
pub mod render;
pub mod tiles;

pub use crate::crs::{Crs, Units};
pub use crate::error::{Error, Result};
pub use crate::extent::Extent;
pub use crate::project::{LayerSummary, Project, ProjectFormat, ProjectInfo};
pub use crate::render::{ImageFormat, RenderSettings, RenderedMap};
pub use crate::tiles::{Tile, TilePlan, ZoomLevelPlan, ZoomRange, MAX_LATITUDE, MAX_ZOOM};

// Re-export styles for convenience — qgis-render is the engine that uses them
pub use qgis_styles::{self as styles, LayerStyle, StyleSheet, Renderer, Symbol, Rgba, Color};

/// The crate version, also reported by `qgis-cli --version`.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
