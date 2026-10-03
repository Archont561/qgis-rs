//! Coordinate reference systems: what `EPSG:3857` means, what normalisation
//! accepts, and where a well-formed-but-unknown code stops being an error.

use qgis_render::*;

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
