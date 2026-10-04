//! The release list: crates are published after everything they depend on,
//! the language-binding cores are not published at all, and a re-run of a
//! published version is recognised however cargo words it.

use rstest::rstest;
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

#[rstest]
#[case::already_uploaded("error: crate version `0.1.0` is already uploaded", true)]
#[case::already_exists("the crate already exists on crates.io", true)]
#[case::a_real_failure("error: failed to verify package tarball", false)]
fn a_duplicate_upload_is_recognised_however_cargo_words_it(
    #[case] message: &str,
    #[case] is_duplicate: bool,
) {
    assert_eq!(already_published(message), is_duplicate, "{message}");
}
