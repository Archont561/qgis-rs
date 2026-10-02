//! `pack-check` and the manifest lint: glob semantics borrowed from an npm
//! `files` list, a report that names every missing entry rather than the
//! first, and the two TOML files kept in taplo's canonical form.

use xtask::lints::{glob_matches, pack_check, CANONICAL_TOML};
use xtask::util::repo_root;

#[test]
fn globs_match_the_way_the_npm_files_list_means_them() {
    let package = repo_root().join("crates/xtask");
    assert!(glob_matches(&package, "src/*.rs").expect("readable"));
    assert!(glob_matches(&package.join("src"), "li*.rs").expect("readable"));
    assert!(!glob_matches(&package, "*.node").expect("readable"));
    // A glob under a directory that does not exist is a miss, not a crash.
    assert!(!glob_matches(&package, "nowhere/*.node").expect("readable"));
}

#[test]
fn pack_check_reports_what_is_missing_rather_than_the_first_failure() {
    let error = pack_check("crates/xtask", &["Cargo.toml".into(), "nope".into()])
        .expect_err("the package is missing an entry");
    assert!(error.to_string().contains("1 entries missing"));
}

#[test]
fn pack_check_passes_on_a_complete_package() {
    pack_check(
        "crates/xtask",
        &["Cargo.toml".into(), "src/".into(), "src/*.rs".into()],
    )
    .expect("xtask ships its own sources");
}

#[test]
fn the_canonical_manifests_are_the_two_pixi_files() {
    for name in CANONICAL_TOML {
        assert!(repo_root().join(name).is_file(), "{name} is gone");
    }
}
