//! qgis-styles — pure style IR, no QGIS dep.
//!
//! The style IR is the single source of truth for symbology:
//! - Python SDK generates it via @style decorators
//! - Rust validates it
//! - qgis-render uses it for offscreen rendering
//! - JS bridge converts it to MapLibre style
//! - CLI/server/MCP accept it as --style
//!
//! ```rust
//! use qgis_styles::{StyleSheet, LayerStyle, Renderer, Symbol, Rgba};
//! let sheet = StyleSheet::new();
//! ```

pub mod color;
pub mod error;
pub mod labeling;
pub mod layout;
pub mod renderer;
pub mod style;
pub mod symbol;

pub use color::{Color, Rgba};
pub use error::{Error, Result};
pub use labeling::{Labeling, LabelPlacement};
pub use layout::{Layout, LayoutItem, LayoutItemType, PageSize};
pub use renderer::{Category, Range, Renderer, Rule};
pub use style::{LayerStyle, StyleSheet};
pub use symbol::{LineSymbol, MarkerSymbol, FillSymbol, Symbol, Stroke};

pub const VERSION: u8 = 1;
