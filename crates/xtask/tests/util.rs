//! The two bits of filesystem knowledge every subcommand starts from: where
//! the repository root is, and which files are the C++ shim.

use xtask::util::{cpp_sources, repo_root};

#[test]
fn the_repository_root_is_the_one_holding_pixi_toml() {
    assert!(repo_root().join("pixi.toml").is_file());
    assert!(repo_root().join("crates/xtask/Cargo.toml").is_file());
}

#[test]
fn the_cpp_walk_finds_the_shim_and_nothing_else() {
    for path in cpp_sources() {
        let extension = path.extension().and_then(std::ffi::OsStr::to_str);
        assert!(matches!(extension, Some("cpp" | "h")), "{}", path.display());
        assert!(path.starts_with(repo_root().join("crates/qgis-sys")));
    }
}
