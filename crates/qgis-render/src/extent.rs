//! Rectangular areas, in whatever CRS produced them.

use crate::error::{Error, Result};

/// An axis-aligned rectangle.
///
/// The CRS is *not* part of the extent: a project extent is in the project CRS,
/// a `--bounds` argument is in EPSG:4326, a tile extent is in EPSG:4326 as well.
/// Keep the CRS next to the value you are working with.
#[derive(Debug, Clone, Copy, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Extent {
    /// Western (or left) edge.
    pub min_x: f64,
    /// Southern (or bottom) edge.
    pub min_y: f64,
    /// Eastern (or right) edge.
    pub max_x: f64,
    /// Northern (or top) edge.
    pub max_y: f64,
}

impl Extent {
    /// Build an extent from its four edges.
    #[must_use]
    pub const fn new(min_x: f64, min_y: f64, max_x: f64, max_y: f64) -> Self {
        Self {
            min_x,
            min_y,
            max_x,
            max_y,
        }
    }

    /// Parse `minx,miny,maxx,maxy`, as accepted by `--extent` and `--bounds`.
    ///
    /// # Errors
    ///
    /// Returns [`Error::InvalidExtent`] if the text does not have four
    /// comma-separated numbers, or if the maximums are smaller than the
    /// minimums.
    pub fn parse(text: &str) -> Result<Self> {
        let parts: Vec<&str> = text.split(',').map(str::trim).collect();
        let invalid = || Error::InvalidExtent {
            value: text.to_string(),
        };
        if parts.len() != 4 {
            return Err(invalid());
        }
        let mut values = [0.0f64; 4];
        for (slot, part) in values.iter_mut().zip(parts) {
            *slot = part.parse::<f64>().map_err(|_| invalid())?;
        }
        let extent = Self::new(values[0], values[1], values[2], values[3]);
        if !extent.is_valid() {
            return Err(invalid());
        }
        Ok(extent)
    }

    /// Width along the x axis.
    #[must_use]
    pub const fn width(&self) -> f64 {
        self.max_x - self.min_x
    }

    /// Height along the y axis.
    #[must_use]
    pub const fn height(&self) -> f64 {
        self.max_y - self.min_y
    }

    /// True when the edges are finite and ordered `min <= max`.
    #[must_use]
    pub fn is_valid(&self) -> bool {
        [self.min_x, self.min_y, self.max_x, self.max_y]
            .iter()
            .all(|value| value.is_finite())
            && self.min_x <= self.max_x
            && self.min_y <= self.max_y
    }

    /// True when the point lies inside the extent, edges included.
    #[must_use]
    pub fn contains(&self, x: f64, y: f64) -> bool {
        x >= self.min_x && x <= self.max_x && y >= self.min_y && y <= self.max_y
    }

    /// True when the two extents share at least one point.
    #[must_use]
    pub fn intersects(&self, other: &Self) -> bool {
        self.min_x <= other.max_x
            && other.min_x <= self.max_x
            && self.min_y <= other.max_y
            && other.min_y <= self.max_y
    }
}

impl std::str::FromStr for Extent {
    type Err = Error;

    fn from_str(text: &str) -> Result<Self> {
        Self::parse(text)
    }
}

impl std::fmt::Display for Extent {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            formatter,
            "{},{},{},{}",
            self.min_x, self.min_y, self.max_x, self.max_y
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_the_cli_form() {
        let extent = Extent::parse("14, 50, 15, 51").expect("valid extent");
        assert_eq!(extent, Extent::new(14.0, 50.0, 15.0, 51.0));
        assert_eq!(extent.width(), 1.0);
        assert_eq!(extent.height(), 1.0);
        assert!(extent.contains(14.5, 50.5));
        assert!(!extent.contains(13.0, 50.5));
    }

    #[test]
    fn round_trips_through_display() {
        let extent = Extent::new(14.0, 50.0, 15.0, 51.0);
        assert_eq!(Extent::parse(&extent.to_string()).expect("round trip"), extent);
    }

    #[test]
    fn rejects_incomplete_and_reversed_extents() {
        for text in ["14,50,15", "a,b,c,d", "15,50,14,51", ""] {
            assert!(Extent::parse(text).is_err(), "{text:?} should not parse");
        }
    }

    #[test]
    fn detects_overlap() {
        let a = Extent::new(0.0, 0.0, 10.0, 10.0);
        assert!(a.intersects(&Extent::new(5.0, 5.0, 20.0, 20.0)));
        assert!(!a.intersects(&Extent::new(20.0, 20.0, 30.0, 30.0)));
    }
}
