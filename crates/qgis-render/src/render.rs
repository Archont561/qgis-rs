//! Render settings and rendered output.

use std::path::{Path, PathBuf};

use crate::crs::Crs;
use crate::error::{Error, Result};
use crate::extent::Extent;

/// Output formats the renderer will eventually support.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ImageFormat {
    /// Portable Network Graphics.
    Png,
    /// JPEG.
    Jpeg,
    /// WebP.
    WebP,
    /// Scalable Vector Graphics.
    Svg,
    /// PDF, for print output.
    Pdf,
}

impl ImageFormat {
    /// Infer the format from a file extension.
    #[must_use]
    pub fn from_extension(extension: &str) -> Option<Self> {
        match extension.to_ascii_lowercase().as_str() {
            "png" => Some(Self::Png),
            "jpg" | "jpeg" => Some(Self::Jpeg),
            "webp" => Some(Self::WebP),
            "svg" => Some(Self::Svg),
            "pdf" => Some(Self::Pdf),
            _ => None,
        }
    }

    /// The canonical file extension, without the dot.
    #[must_use]
    pub const fn extension(&self) -> &'static str {
        match self {
            Self::Png => "png",
            Self::Jpeg => "jpg",
            Self::WebP => "webp",
            Self::Svg => "svg",
            Self::Pdf => "pdf",
        }
    }

    /// The MIME type a server would send for this format.
    #[must_use]
    pub const fn mime_type(&self) -> &'static str {
        match self {
            Self::Png => "image/png",
            Self::Jpeg => "image/jpeg",
            Self::WebP => "image/webp",
            Self::Svg => "image/svg+xml",
            Self::Pdf => "application/pdf",
        }
    }

    /// True for formats that are raster images rather than documents.
    #[must_use]
    pub const fn is_raster(&self) -> bool {
        matches!(self, Self::Png | Self::Jpeg | Self::WebP)
    }
}

/// How to render a project.
///
/// Defaults match `qgis-cli render`: 1024×768 pixels at 96 dpi, in the
/// project's own CRS, over the full extent.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct RenderSettings {
    /// Where the image is written. `-` means stdout.
    pub output: PathBuf,
    /// Output format, inferred from the output path unless set explicitly.
    pub format: ImageFormat,
    /// Image width in pixels.
    pub width: u32,
    /// Image height in pixels.
    pub height: u32,
    /// Resolution in dots per inch.
    pub dpi: f64,
    /// CRS to render in; `None` keeps the project CRS.
    pub crs: Option<Crs>,
    /// Area to render; `None` uses the full extent.
    pub extent: Option<Extent>,
    /// Layers to draw; empty means all of them.
    pub layers: Vec<String>,
    /// Print layout to render instead of the map canvas.
    pub layout: Option<String>,
    /// Style overrides — from qgis-styles IR.
    #[serde(default)]
    pub style: Option<qgis_styles::StyleSheet>,
    /// Per-layer style overrides.
    #[serde(default)]
    pub layer_styles: std::collections::HashMap<String, qgis_styles::LayerStyle>,
}

impl RenderSettings {
    /// Settings for writing to `output`, with the format taken from its
    /// extension.
    ///
    /// # Errors
    ///
    /// Returns [`Error::UnknownImageFormat`] when the extension is not a
    /// supported format.
    pub fn new(output: impl AsRef<Path>) -> Result<Self> {
        let output = output.as_ref();
        let extension = output
            .extension()
            .and_then(|extension| extension.to_str())
            .unwrap_or_default();
        let format =
            ImageFormat::from_extension(extension).ok_or_else(|| Error::UnknownImageFormat {
                path: output.to_path_buf(),
            })?;
        Ok(Self {
            output: output.to_path_buf(),
            format,
            width: 1024,
            height: 768,
            dpi: 96.0,
            crs: None,
            extent: None,
            layers: Vec::new(),
            layout: None,
            style: None,
            layer_styles: std::collections::HashMap::new(),
        })
    }

    /// Set the pixel size.
    #[must_use]
    pub const fn with_size(mut self, width: u32, height: u32) -> Self {
        self.width = width;
        self.height = height;
        self
    }

    /// Set the resolution.
    #[must_use]
    pub const fn with_dpi(mut self, dpi: f64) -> Self {
        self.dpi = dpi;
        self
    }

    /// Set the CRS to render in.
    #[must_use]
    pub fn with_crs(mut self, crs: Crs) -> Self {
        self.crs = Some(crs);
        self
    }

    /// Set the area to render.
    #[must_use]
    pub const fn with_extent(mut self, extent: Extent) -> Self {
        self.extent = Some(extent);
        self
    }

    /// Restrict rendering to these layers.
    #[must_use]
    pub fn with_layers(mut self, layers: impl IntoIterator<Item = String>) -> Self {
        self.layers = layers.into_iter().collect();
        self
    }

    /// Render a named print layout instead of the map canvas.
    #[must_use]
    pub fn with_layout(mut self, layout: impl Into<String>) -> Self {
        self.layout = Some(layout.into());
        self
    }

    /// Set style overrides.
    #[must_use]
    pub fn with_style(mut self, style: qgis_styles::StyleSheet) -> Self {
        self.style = Some(style);
        self
    }

    /// Set per-layer style.
    #[must_use]
    pub fn with_layer_style(mut self, layer: impl Into<String>, style: qgis_styles::LayerStyle) -> Self {
        self.layer_styles.insert(layer.into(), style);
        self
    }
}

/// A rendered image, once rendering exists.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct RenderedMap {
    /// Where the image was written.
    pub path: PathBuf,
    /// The format it was written in.
    pub format: ImageFormat,
    /// Size on disk, in bytes.
    pub bytes: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn infers_the_format_from_the_output_path() {
        for (name, format) in [
            ("map.png", ImageFormat::Png),
            ("map.JPG", ImageFormat::Jpeg),
            ("map.webp", ImageFormat::WebP),
            ("map.svg", ImageFormat::Svg),
            ("map.pdf", ImageFormat::Pdf),
        ] {
            let settings = RenderSettings::new(name).expect("known format");
            assert_eq!(settings.format, format, "{name}");
            assert_eq!(settings.width, 1024);
            assert_eq!(settings.height, 768);
            assert_eq!(settings.dpi, 96.0);
        }
        assert!(RenderSettings::new("map.bmp").is_err());
        assert!(RenderSettings::new("map").is_err());
    }

    #[test]
    fn builders_accumulate() {
        let settings = RenderSettings::new("out.png")
            .expect("png")
            .with_size(2048, 1536)
            .with_dpi(300.0)
            .with_crs(Crs::web_mercator())
            .with_extent(Extent::new(14.0, 50.0, 15.0, 51.0))
            .with_layers(["buildings".to_string(), "roads".to_string()])
            .with_layout("A4 Landscape");

        assert_eq!((settings.width, settings.height), (2048, 1536));
        assert_eq!(settings.dpi, 300.0);
        assert_eq!(settings.crs, Some(Crs::web_mercator()));
        assert_eq!(settings.layers, vec!["buildings", "roads"]);
        assert_eq!(settings.layout.as_deref(), Some("A4 Landscape"));
    }

    #[test]
    fn formats_know_their_mime_types() {
        assert_eq!(ImageFormat::Png.mime_type(), "image/png");
        assert_eq!(ImageFormat::Svg.mime_type(), "image/svg+xml");
        assert_eq!(ImageFormat::Pdf.mime_type(), "application/pdf");
        assert!(ImageFormat::Png.is_raster());
        assert!(!ImageFormat::Pdf.is_raster());
    }
}
