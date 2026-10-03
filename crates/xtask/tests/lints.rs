//! `pack-check` and the manifest lint: glob semantics borrowed from an npm
//! `files` list, a report that names every missing entry rather than the
//! first, and the two TOML files kept in taplo's canonical form.

use xtask::lints::{check_sources, glob_matches, looks_like_source, pack_check, CANONICAL_TOML};
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

#[test]
fn a_hidden_python_module_is_source_and_a_generated_declaration_is_not() {
    // The two files the ignore rule actually swallowed.
    assert!(looks_like_source(
        "py-packages/qgis-rs/python/qgis_rs/_api.py"
    ));
    assert!(looks_like_source(
        "py-packages/qgis-rs/python/qgis_rs/_transport.py"
    ));
    // Generated, dot-prefixed, and ignored on purpose.
    assert!(!looks_like_source(
        "ts-packages/qgis-node/.napi-generated.d.ts"
    ));
    // Build output under a source tree.
    assert!(!looks_like_source(
        "ts-packages/qgis-node/node_modules/left-pad/index.js"
    ));
    assert!(!looks_like_source(
        "py-packages/qgis-rs/python/qgis_rs/__pycache__/cli.pyc"
    ));
    assert!(!looks_like_source(
        "py-packages/qgis-rs/dist/qgis_rs-0.1.0.whl"
    ));
}

#[test]
fn no_source_file_in_this_repository_is_hidden_from_git() {
    check_sources().expect("every source file is committed or committable");
}
