//! `pack-check` and the manifest lint: glob semantics borrowed from an npm
//! `files` list, a report that names every missing entry rather than the
//! first, and the TOML files kept in taplo's canonical form.

use xtask::lints::{
    check_sources, clang_tidy_arguments, first_matching_file, glob_matches, looks_like_source,
    pack_check, CANONICAL_TOML,
};
use xtask::util::{cpp_sources, repo_root};

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
fn the_canonical_manifests_are_the_one_pixi_file() {
    for name in CANONICAL_TOML {
        assert!(repo_root().join(name).is_file(), "{name} is gone");
    }
}

/// The shim's `.cpp` files are discovered for clang-tidy, and clang-tidy is
/// handed the compiler flags *after* the `--` separator — which is the mistake
/// the shell version made, and the one clang-tidy answers with its own `--help`
/// and exit 123.
#[test]
fn clang_tidy_gets_its_sources_before_the_separator_and_its_flags_after() {
    let sources: Vec<std::path::PathBuf> = cpp_sources()
        .into_iter()
        .filter(|path| path.extension().is_some_and(|extension| extension == "cpp"))
        .collect();
    assert!(
        !sources.is_empty(),
        "the shim has .cpp files; a discovery that finds none would run clang-tidy on nothing"
    );

    let args = clang_tidy_arguments(
        std::path::Path::new("/shim"),
        std::path::Path::new("/prefix"),
        std::path::Path::new("/prefix/include/qt"),
        std::path::Path::new("/out/cxxbridge"),
        std::path::Path::new("/gcc/include"),
        &sources,
    );

    let separator = args
        .iter()
        .position(|arg| arg == "--")
        .expect("clang-tidy needs the `--` before the compiler flags");
    for source in &sources {
        let position = args
            .iter()
            .position(|arg| arg == &source.display().to_string())
            .unwrap_or_else(|| panic!("{} is not on the command line", source.display()));
        assert!(
            position < separator,
            "{} landed after `--`, where clang-tidy reads it as a compiler flag",
            source.display()
        );
    }

    let flags = &args[separator + 1..];
    for expected in [
        "-std=c++17",
        "-I/shim",
        "-I/shim/include",
        "-I/out/cxxbridge/include",
        "-I/out/cxxbridge/crate",
        "-I/prefix/include/qgis",
    ] {
        assert!(flags.iter().any(|flag| flag == expected), "no {expected}");
    }
    assert!(
        flags.iter().all(|flag| !flag.contains("qgis-sys/../")),
        "an include path that walks out of the shim is a relative path that no longer resolves"
    );
    assert!(
        flags
            .iter()
            .filter(|flag| flag.starts_with("-I"))
            .all(|flag| flag.len() > 2 && flag[2..].starts_with('/')),
        "every include path is absolute: a subcommand runs at the repository root"
    );
    // The GCC internal include dir carrying stddef.h is only reachable as an
    // extra arg: it is a clang driver flag, not part of the compiler command
    // line clang-tidy forwards to the parser.
    assert!(
        args.iter().any(|arg| arg == "--extra-arg=-I/gcc/include"),
        "the GCC internal include dir is missing"
    );
}

/// Qt is found under `include/qt` or `include/qt6` depending on the build, and
/// the four Qt module directories have to follow whichever one it is.
#[test]
fn clang_tidy_names_every_qt_module_directory() {
    let args = clang_tidy_arguments(
        std::path::Path::new("/shim"),
        std::path::Path::new("/prefix"),
        std::path::Path::new("/prefix/include/qt6"),
        std::path::Path::new("/out/cxxbridge"),
        std::path::Path::new("/gcc/include"),
        &[std::path::PathBuf::from("/shim/application.cpp")],
    );
    for module in ["QtCore", "QtGui", "QtWidgets", "QtXml"] {
        assert!(
            args.iter().any(|arg| arg.ends_with(&format!("/{module}"))),
            "no include path for {module}"
        );
    }
}

/// Which of several equally valid matches clang-tidy gets must not depend on
/// the order the filesystem hands them back, or the lint fails on one machine
/// and passes on another.
#[test]
fn discovery_picks_the_same_match_whatever_order_the_tree_is_walked_in() {
    let root = std::env::temp_dir().join("xtask-first-matching-file");
    let _ = std::fs::remove_dir_all(&root);
    for name in ["13.2.0", "11.3.0"] {
        let directory = root.join(name);
        std::fs::create_dir_all(&directory).expect("writable temp dir");
        std::fs::write(directory.join("stddef.h"), "").expect("writable temp dir");
    }

    let found = first_matching_file(&root, |path| {
        path.file_name().is_some_and(|name| name == "stddef.h")
    })
    .expect("two matches exist");
    assert_eq!(
        found.parent().and_then(std::path::Path::file_name),
        Some(std::ffi::OsStr::new("11.3.0")),
        "the numerically-and-alphabetically first match is the answer, not the first found"
    );

    assert!(
        first_matching_file(&root, |_| false).is_none(),
        "no match is None, not an error"
    );
    let _ = std::fs::remove_dir_all(&root);
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
