//! Renderers — single, categorized, graduated, rule-based.

use crate::symbol::Symbol;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Category {
    pub value: String,
    pub label: String,
    pub symbol: Symbol,
    #[serde(default)]
    pub render: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Range {
    pub lower: f64,
    pub upper: f64,
    pub label: String,
    pub symbol: Symbol,
    #[serde(default)]
    pub render: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Rule {
    pub filter: String, // QGIS expression
    pub label: String,
    pub symbol: Symbol,
    #[serde(default)]
    pub else_rule: bool,
    #[serde(default)]
    pub scale_min: Option<f64>,
    #[serde(default)]
    pub scale_max: Option<f64>,
}

/// Renderer type — subset of QGIS renderers.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Renderer {
    SingleSymbol {
        symbol: Symbol,
    },
    Categorized {
        attr: String,
        categories: Vec<Category>,
        #[serde(default)]
        default_symbol: Option<Symbol>,
    },
    Graduated {
        attr: String,
        ranges: Vec<Range>,
        #[serde(default)]
        mode: Option<String>, // equal_interval, quantile, etc.
    },
    RuleBased {
        rules: Vec<Rule>,
    },
    NoSymbol,
}

impl Renderer {
    pub fn single(symbol: Symbol) -> Self {
        Self::SingleSymbol { symbol }
    }

    pub fn categorized(attr: impl Into<String>, categories: Vec<Category>) -> Self {
        Self::Categorized {
            attr: attr.into(),
            categories,
            default_symbol: None,
        }
    }

    pub fn is_valid(&self) -> bool {
        match self {
            Self::SingleSymbol { .. } => true,
            Self::Categorized { categories, .. } => !categories.is_empty(),
            Self::Graduated { ranges, .. } => !ranges.is_empty(),
            Self::RuleBased { rules } => !rules.is_empty(),
            Self::NoSymbol => true,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::color::Rgba;

    #[test]
    fn validates_renderer() {
        let sym = Symbol::fill(Rgba::new(255, 0, 0));
        let single = Renderer::single(sym);
        assert!(single.is_valid());

        let empty_cat = Renderer::Categorized {
            attr: "type".to_string(),
            categories: vec![],
            default_symbol: None,
        };
        assert!(!empty_cat.is_valid());
    }
}
