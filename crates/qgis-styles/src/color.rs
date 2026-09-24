//! Colors — Rgba and named colors.

use crate::error::{Error, Result};
use serde::{Deserialize, Serialize};

/// RGBA color, 0-255 per channel.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Rgba {
    pub r: u8,
    pub g: u8,
    pub b: u8,
    #[serde(default = "default_alpha")]
    pub a: u8,
}

fn default_alpha() -> u8 {
    255
}

impl Rgba {
    pub const fn new(r: u8, g: u8, b: u8) -> Self {
        Self { r, g, b, a: 255 }
    }

    pub const fn with_alpha(r: u8, g: u8, b: u8, a: u8) -> Self {
        Self { r, g, b, a }
    }

    pub const fn transparent() -> Self {
        Self {
            r: 0,
            g: 0,
            b: 0,
            a: 0,
        }
    }

    pub fn from_hex(hex: &str) -> Result<Self> {
        let hex = hex.trim().trim_start_matches('#');
        match hex.len() {
            6 => {
                let r = u8::from_str_radix(&hex[0..2], 16).map_err(|_| Error::InvalidColor {
                    value: hex.to_string(),
                })?;
                let g = u8::from_str_radix(&hex[2..4], 16).map_err(|_| Error::InvalidColor {
                    value: hex.to_string(),
                })?;
                let b = u8::from_str_radix(&hex[4..6], 16).map_err(|_| Error::InvalidColor {
                    value: hex.to_string(),
                })?;
                Ok(Self::new(r, g, b))
            }
            8 => {
                let r = u8::from_str_radix(&hex[0..2], 16).map_err(|_| Error::InvalidColor {
                    value: hex.to_string(),
                })?;
                let g = u8::from_str_radix(&hex[2..4], 16).map_err(|_| Error::InvalidColor {
                    value: hex.to_string(),
                })?;
                let b = u8::from_str_radix(&hex[4..6], 16).map_err(|_| Error::InvalidColor {
                    value: hex.to_string(),
                })?;
                let a = u8::from_str_radix(&hex[6..8], 16).map_err(|_| Error::InvalidColor {
                    value: hex.to_string(),
                })?;
                Ok(Self::with_alpha(r, g, b, a))
            }
            _ => Err(Error::InvalidColor {
                value: hex.to_string(),
            }),
        }
    }

    pub fn to_hex(&self) -> String {
        if self.a == 255 {
            format!("#{:02x}{:02x}{:02x}", self.r, self.g, self.b)
        } else {
            format!("#{:02x}{:02x}{:02x}{:02x}", self.r, self.g, self.b, self.a)
        }
    }

    pub fn to_rgba_string(&self) -> String {
        format!(
            "rgba({},{},{},{:.2})",
            self.r,
            self.g,
            self.b,
            self.a as f32 / 255.0
        )
    }
}

/// Named color or RGBA.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Color {
    Rgba(Rgba),
    Hex(String),
    Named(String),
}

impl Color {
    pub fn parse(s: &str) -> Result<Self> {
        if s.starts_with('#') {
            let rgba = Rgba::from_hex(s)?;
            Ok(Self::Rgba(rgba))
        } else if s.starts_with("rgba") || s.starts_with("rgb") {
            // Simplified: keep as named for now, full parsing later
            Ok(Self::Named(s.to_string()))
        } else {
            Ok(Self::Named(s.to_string()))
        }
    }

    pub fn to_rgba(&self) -> Result<Rgba> {
        match self {
            Self::Rgba(rgba) => Ok(*rgba),
            Self::Hex(hex) => Rgba::from_hex(hex),
            Self::Named(name) => {
                // Basic named colors
                match name.to_lowercase().as_str() {
                    "red" => Ok(Rgba::new(255, 0, 0)),
                    "green" => Ok(Rgba::new(0, 128, 0)),
                    "blue" => Ok(Rgba::new(0, 0, 255)),
                    "black" => Ok(Rgba::new(0, 0, 0)),
                    "white" => Ok(Rgba::new(255, 255, 255)),
                    "transparent" => Ok(Rgba::transparent()),
                    _ => Err(Error::InvalidColor {
                        value: name.clone(),
                    }),
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_hex_colors() {
        let red = Rgba::from_hex("#ff0000").unwrap();
        assert_eq!(red, Rgba::new(255, 0, 0));
        assert_eq!(red.to_hex(), "#ff0000");

        let with_alpha = Rgba::from_hex("#ff000080").unwrap();
        assert_eq!(with_alpha.a, 128);
    }

    #[test]
    fn rejects_invalid_hex() {
        assert!(Rgba::from_hex("#xyz").is_err());
        assert!(Rgba::from_hex("#12345").is_err());
    }
}
