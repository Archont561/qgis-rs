//! Print layouts — page, map, legend, scalebar.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PageSize {
    pub width_mm: f64,
    pub height_mm: f64,
    pub name: Option<String>, // A4, A3, etc.
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LayoutItemType {
    Map,
    Legend,
    ScaleBar,
    Label,
    Picture,
    Shape,
    NorthArrow,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LayoutItem {
    pub id: String,
    pub item_type: LayoutItemType,
    pub x_mm: f64,
    pub y_mm: f64,
    pub width_mm: f64,
    pub height_mm: f64,
    #[serde(default)]
    pub properties: Option<serde_json::Value>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Layout {
    pub name: String,
    pub page: PageSize,
    #[serde(default)]
    pub items: Vec<LayoutItem>,
    #[serde(default)]
    pub dpi: Option<f64>,
}

impl Layout {
    pub fn new(name: impl Into<String>, page: PageSize) -> Self {
        Self {
            name: name.into(),
            page,
            items: vec![],
            dpi: Some(300.0),
        }
    }
}
