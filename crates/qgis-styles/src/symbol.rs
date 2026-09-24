//! Symbols — marker, line, fill.

use crate::color::Rgba;
use serde::{Deserialize, Serialize};

/// Stroke for line and outline.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Stroke {
    #[serde(default)]
    pub color: Option<Rgba>,
    #[serde(default = "default_width")]
    pub width: f64,
    #[serde(default)]
    pub dash: Option<Vec<f64>>,
    #[serde(default)]
    pub opacity: Option<f64>,
}

fn default_width() -> f64 {
    1.0
}

impl Default for Stroke {
    fn default() -> Self {
        Self {
            color: Some(Rgba::new(0, 0, 0)),
            width: 1.0,
            dash: None,
            opacity: None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MarkerSymbol {
    #[serde(default)]
    pub color: Option<Rgba>,
    #[serde(default = "default_marker_size")]
    pub size: f64,
    #[serde(default)]
    pub stroke: Option<Stroke>,
    #[serde(default)]
    pub shape: Option<String>, // circle, square, triangle, etc.
    #[serde(default)]
    pub opacity: Option<f64>,
}

fn default_marker_size() -> f64 {
    6.0
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LineSymbol {
    #[serde(default)]
    pub color: Option<Rgba>,
    #[serde(default = "default_width")]
    pub width: f64,
    #[serde(default)]
    pub dash: Option<Vec<f64>>,
    #[serde(default)]
    pub opacity: Option<f64>,
    #[serde(default)]
    pub cap: Option<String>, // butt, round, square
    #[serde(default)]
    pub join: Option<String>, // miter, round, bevel
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FillSymbol {
    #[serde(default)]
    pub color: Option<Rgba>,
    #[serde(default)]
    pub outline: Option<Box<Stroke>>,
    #[serde(default)]
    pub opacity: Option<f64>,
    #[serde(default)]
    pub pattern: Option<String>, // solid, hatch, etc.
}

/// Unified symbol enum.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Symbol {
    Marker(MarkerSymbol),
    Line(LineSymbol),
    Fill(FillSymbol),
}

impl Symbol {
    pub fn marker(color: Rgba, size: f64) -> Self {
        Self::Marker(MarkerSymbol {
            color: Some(color),
            size,
            stroke: None,
            shape: Some("circle".to_string()),
            opacity: None,
        })
    }

    pub fn line(color: Rgba, width: f64) -> Self {
        Self::Line(LineSymbol {
            color: Some(color),
            width,
            dash: None,
            opacity: None,
            cap: None,
            join: None,
        })
    }

    pub fn fill(color: Rgba) -> Self {
        Self::Fill(FillSymbol {
            color: Some(color),
            outline: None,
            opacity: None,
            pattern: None,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn creates_symbols() {
        let red = Rgba::new(255, 0, 0);
        let marker = Symbol::marker(red, 8.0);
        assert!(matches!(marker, Symbol::Marker(_)));

        let line = Symbol::line(red, 2.0);
        assert!(matches!(line, Symbol::Line(_)));
    }

    #[test]
    fn serializes_symbols() {
        let sym = Symbol::fill(Rgba::new(0, 255, 0));
        let json = serde_json::to_string(&sym).unwrap();
        assert!(json.contains("fill"));
    }
}
