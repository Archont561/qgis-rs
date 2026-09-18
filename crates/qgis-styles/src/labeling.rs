//! Labeling — PAL labeling subset.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LabelPlacement {
    Point,
    Line,
    AroundPoint,
    OverPoint,
    Curved,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Labeling {
    pub field: String,
    #[serde(default)]
    pub placement: Option<LabelPlacement>,
    #[serde(default)]
    pub size: Option<f64>,
    #[serde(default)]
    pub color: Option<String>,
    #[serde(default)]
    pub buffer: Option<bool>,
    #[serde(default)]
    pub expression: Option<String>, // QGIS expression for label
}

impl Labeling {
    pub fn new(field: impl Into<String>) -> Self {
        Self {
            field: field.into(),
            placement: None,
            size: None,
            color: None,
            buffer: None,
            expression: None,
        }
    }
}
