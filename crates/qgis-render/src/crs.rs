//! Coordinate reference systems, identified by authority code.

use crate::error::{Error, Result};

/// A coordinate reference system, addressed by its authority code
/// (`EPSG:3857`).
///
/// Only well-known codes carry a name and units here; anything else is accepted
/// but reported as [`Units::Unknown`] rather than rejected, so that unusual
/// projects still round-trip through the CLI.
#[derive(Debug, Clone, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct Crs {
    auth_id: String,
}

/// The unit a CRS measures in.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Units {
    /// Decimal degrees — a geographic CRS.
    Degrees,
    /// Metres — a projected CRS.
    Meters,
    /// The code is not in the built-in table.
    Unknown,
}

/// A handful of CRS codes qgis-rs knows about without asking QGIS.
const KNOWN: &[(&str, &str, Units, bool)] = &[
    ("EPSG:4326", "WGS 84", Units::Degrees, true),
    ("EPSG:4258", "ETRS89", Units::Degrees, true),
    (
        "EPSG:3857",
        "WGS 84 / Pseudo-Mercator",
        Units::Meters,
        false,
    ),
    ("EPSG:32633", "WGS 84 / UTM zone 33N", Units::Meters, false),
    ("EPSG:2180", "ETRS89 / Poland CS92", Units::Meters, false),
];

impl Crs {
    /// WGS 84 geographic coordinates (EPSG:4326).
    #[must_use]
    pub fn wgs84() -> Self {
        Self {
            auth_id: "EPSG:4326".to_string(),
        }
    }

    /// Web Mercator, the CRS every XYZ tile pyramid uses (EPSG:3857).
    #[must_use]
    pub fn web_mercator() -> Self {
        Self {
            auth_id: "EPSG:3857".to_string(),
        }
    }

    /// Parse an authority code.
    ///
    /// # Errors
    ///
    /// Returns [`Error::UnknownCrs`] unless the text looks like
    /// `AUTHORITY:CODE`, for example `EPSG:3857`.
    pub fn from_auth_id(auth_id: &str) -> Result<Self> {
        let trimmed = auth_id.trim();
        let (authority, code) = trimmed.split_once(':').ok_or_else(|| Error::UnknownCrs {
            auth_id: auth_id.to_string(),
        })?;
        let valid = !authority.is_empty()
            && authority
                .chars()
                .all(|character| character.is_ascii_alphabetic())
            && !code.is_empty()
            && code.chars().all(|character| character.is_ascii_digit());
        if !valid {
            return Err(Error::UnknownCrs {
                auth_id: auth_id.to_string(),
            });
        }
        Ok(Self {
            auth_id: trimmed.to_uppercase(),
        })
    }

    /// The authority code, uppercased.
    #[must_use]
    pub fn auth_id(&self) -> &str {
        &self.auth_id
    }

    /// A human-readable name, if the code is in the built-in table.
    #[must_use]
    pub fn name(&self) -> Option<&'static str> {
        self.entry().map(|entry| entry.1)
    }

    /// What the CRS measures in.
    #[must_use]
    pub fn units(&self) -> Units {
        self.entry().map_or(Units::Unknown, |entry| entry.2)
    }

    /// True for the geographic codes qgis-rs knows; false for projected codes
    /// and for anything not in the table.
    #[must_use]
    pub fn is_geographic(&self) -> bool {
        self.entry().is_some_and(|entry| entry.3)
    }

    fn entry(&self) -> Option<&'static (&'static str, &'static str, Units, bool)> {
        KNOWN.iter().find(|entry| entry.0 == self.auth_id)
    }
}

impl std::str::FromStr for Crs {
    type Err = Error;

    fn from_str(text: &str) -> Result<Self> {
        Self::from_auth_id(text)
    }
}

impl std::fmt::Display for Crs {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.auth_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn knows_the_web_mercator_crs() {
        let crs = Crs::web_mercator();
        assert_eq!(crs.auth_id(), "EPSG:3857");
        assert_eq!(crs.name(), Some("WGS 84 / Pseudo-Mercator"));
        assert_eq!(crs.units(), Units::Meters);
        assert!(!crs.is_geographic());
    }

    #[test]
    fn normalises_case_and_whitespace() {
        let crs = Crs::from_auth_id(" epsg:2180 ").expect("valid code");
        assert_eq!(crs.auth_id(), "EPSG:2180");
        assert_eq!(crs.name(), Some("ETRS89 / Poland CS92"));
    }

    #[test]
    fn accepts_unknown_but_wellformed_codes() {
        let crs = Crs::from_auth_id("EPSG:2154").expect("valid shape");
        assert_eq!(crs.auth_id(), "EPSG:2154");
        assert_eq!(crs.units(), Units::Unknown);
        assert_eq!(crs.name(), None);
        assert!(!crs.is_geographic());
    }

    #[test]
    fn rejects_malformed_codes() {
        for text in ["3857", "EPSG", "EPSG:abc", ":4326", "EPSG:"] {
            assert!(Crs::from_auth_id(text).is_err(), "{text:?} should fail");
        }
    }
}
