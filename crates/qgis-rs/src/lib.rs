//! `qgis-rs` — the qgis-rs engines behind feature flags.
//!
//! Depend on this crate instead of the engine crates when a caller wants more
//! than one of them. Each engine is re-exported under its short name, and only
//! when its feature is enabled:
//!
//! | feature  | module           | crate            |
//! |----------|------------------|------------------|
//! | `render` | `qgis_rs::render` | `qgis-render`    |
//! | `server` | `qgis_rs::server` | `qgis-server`    |
//! | `styles` | `qgis_rs::styles` | `qgis-styles`    |
//! | `cli`    | `qgis_rs::cli`    | `qgis-cli`       |
//!
//! `render` is on by default. `server` implies the render engine it serves.

#[cfg(feature = "render")]
pub use qgis_render as render;

#[cfg(feature = "server")]
pub use qgis_server as server;

#[cfg(feature = "styles")]
pub use qgis_styles as styles;

#[cfg(feature = "cli")]
pub use qgis_cli as cli;
