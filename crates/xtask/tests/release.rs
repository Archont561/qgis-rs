//! The release list: crates are published after everything they depend on,
//! the language-binding cores are not published at all, and a re-run of a
//! published version is recognised however cargo words it.

use xtask::release::{already_published, CRATES};

#[test]
fn the_publish_order_puts_a_crate_after_everything_it_depends_on() {
    let position = |name: &str| {
        CRATES
            .iter()
            .position(|crate_name| *crate_name == name)
            .unwrap_or_else(|| panic!("{name} is not published"))
    };
    assert!(position("qgis-protocol") < position("qgis-engine"));
    assert!(position("qgis-render") < position("qgis-engine"));
    assert!(position("qgis-render") < position("qgis-cli"));
    assert!(position("qgis-styles") < position("qgis-render"));
}

#[test]
fn the_published_set_excludes_the_language_binding_cores() {
    for excluded in ["qgis-py", "qgis-node", "qgis-sdk", "xtask"] {
        assert!(
            !CRATES.contains(&excluded),
            "{excluded} must not be published"
        );
    }
}

#[test]
fn a_duplicate_upload_is_recognised_however_cargo_words_it() {
    assert!(already_published(
        "error: crate version `0.1.0` is already uploaded"
    ));
    assert!(already_published("the crate already exists on crates.io"));
    assert!(!already_published(
        "error: failed to verify package tarball"
    ));
}
