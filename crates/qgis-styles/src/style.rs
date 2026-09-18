//! StyleSheet — collection of layer styles.

use crate::labeling::Labeling;
use crate::renderer::Renderer;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LayerStyle {
    #[serde(default)]
    pub opacity: Option<f64>,
    pub renderer: Renderer,
    #[serde(default)]
    pub labeling: Option<Labeling>,
    /// Escape hatch: raw QGIS JSON/XML passthrough for unsupported props.
    #[serde(default)]
    pub raw: Option<serde_json::Value>,
    #[serde(default)]
    pub blend_mode: Option<String>,
    #[serde(default)]
    pub visible: Option<bool>,
}

impl LayerStyle {
    pub fn new(renderer: Renderer) -> Self {
        Self {
            opacity: None,
            renderer,
            labeling: None,
            raw: None,
            blend_mode: None,
            visible: None,
        }
    }

    pub fn with_opacity(mut self, opacity: f64) -> Self {
        self.opacity = Some(opacity);
        self
    }

    pub fn with_labeling(mut self, labeling: Labeling) -> Self {
        self.labeling = Some(labeling);
        self
    }

    pub fn is_valid(&self) -> bool {
        self.renderer.is_valid() && self.opacity.map_or(true, |o| (0.0..=1.0).contains(&o))
    }
}

/// Versioned stylesheet — top-level container.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StyleSheet {
    #[serde(default = "default_version")]
    pub version: u8,
    #[serde(default)]
    pub layers: HashMap<String, LayerStyle>,
    #[serde(default)]
    pub name: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
}

fn default_version() -> u8 { 1 }

impl StyleSheet {
    pub fn new() -> Self {
        Self {
            version: 1,
            layers: HashMap::new(),
            name: None,
            description: None,
        }
    }

    pub fn with_layer(mut self, layer_id: impl Into<String>, style: LayerStyle) -> Self {
        self.layers.insert(layer_id.into(), style);
        self
    }

    pub fn get_layer(&self, layer_id: &str) -> Option<&LayerStyle> {
        self.layers.get(layer_id)
    }

    pub fn is_valid(&self) -> bool {
        self.layers.values().all(|s| s.is_valid())
    }

    pub fn from_json(json: &str) -> crate::error::Result<Self> {
        let sheet: Self = serde_json::from_str(json)?;
        if !sheet.is_valid() {
            return Err(crate::error::Error::InvalidStyle { reason: "one or more layer styles invalid".to_string() });
        }
        Ok(sheet)
    }

    pub fn to_json(&self) -> crate::error::Result<String> {
        Ok(serde_json::to_string_pretty(self)?)
    }

    pub fn from_file(path: impl AsRef<std::path::Path>) -> crate::error::Result<Self> {
        let content = std::fs::read_to_string(path)?;
        Self::from_json(&content)
    }

    /// Convert to MapLibre style JSON (simplified).
    pub fn to_maplibre(&self) -> serde_json::Value {
        // Simplified conversion — real impl would map renderers to MapLibre layers
        let mut layers = Vec::new();
        for (id, style) in &self.layers {
            let layer_json = serde_json::json!({
                "id": id,
                "type": match &style.renderer {
                    Renderer::SingleSymbol { symbol } => match symbol {
                        crate::symbol::Symbol::Marker(_) => "circle",
                        crate::symbol::Symbol::Line(_) => "line",
                        crate::symbol::Symbol::Fill(_) => "fill",
                    },
                    _ => "fill",
                },
                "paint": {},
                "layout": {},
            });
            layers.push(layer_json);
        }
        serde_json::json!({
            "version": 8,
            "name": self.name.as_deref().unwrap_or("qgis-rs style"),
            "layers": layers,
        })
    }
}

impl Default for StyleSheet {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::color::Rgba;
    use crate::symbol::Symbol;

    #[test]
    fn creates_stylesheet() {
        let sym = Symbol::fill(Rgba::new(255, 0, 0));
        let renderer = Renderer::single(sym);
        let style = LayerStyle::new(renderer).with_opacity(0.8);
        assert!(style.is_valid());

        let sheet = StyleSheet::new().with_layer("buildings", style);
        assert_eq!(sheet.layers.len(), 1);
        assert!(sheet.is_valid());
    }

    #[test]
    fn round_trips_json() {
        let sym = Symbol::fill(Rgba::new(0, 255, 0));
        let sheet = StyleSheet::new()
            .with_layer("roads", LayerStyle::new(Renderer::single(sym)));
        let json = sheet.to_json().unwrap();
        let parsed = StyleSheet::from_json(&json).unwrap();
        assert_eq!(parsed.layers.len(), 1);
    }

    #[test]
    fn converts_to_maplibre() {
        let sym = Symbol::fill(Rgba::new(0, 0, 255));
        let sheet = StyleSheet::new().with_layer("water", LayerStyle::new(Renderer::single(sym)));
        let ml = sheet.to_maplibre();
        assert_eq!(ml["version"], 8);
    }
}
