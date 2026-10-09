//! `pack-check` and the manifest lint: glob semantics borrowed from an npm
//! `files` list, a report that names every missing entry rather than the
//! first, and the TOML files kept in taplo's canonical form.

use rstest::rstest;
use xtask::lints::{
    check_sources, clang_tidy_arguments, first_matching_file, glob_matches, looks_like_source,
    pack_check, setup_qca_in, QcaRepair, CANONICAL_TOML, COMPILED_CPP_DIR,
};
use xtask::util::{cpp_sources, repo_root};

#[rstest]
#[case::a_directory_prefix("", "src/*.rs", true)]
#[case::a_stem_prefix("src", "li*.rs", true)]
#[case::no_such_extension("", "*.node", false)]
// A glob under a directory that does not exist is a miss, not a crash.
#[case::no_such_directory("", "nowhere/*.node", false)]
fn globs_match_the_way_the_npm_files_list_means_them(
    #[case] under: &str,
    #[case] glob: &str,
    #[case] matches: bool,
) {
    let package = repo_root().join("crates/xtask").join(under);
    assert_eq!(glob_matches(&package, glob).expect("readable"), matches);
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

/// The shim's `.cpp` files are discovered for clang-tidy, and the command
/// consumes the native-manager compile database rather than inventing a second
/// list of QGIS or Qt include paths.
#[test]
fn clang_tidy_uses_the_compile_database_for_native_sources() {
    let sources: Vec<std::path::PathBuf> = cpp_sources()
        .into_iter()
        .filter(|path| path.extension().is_some_and(|extension| extension == "cpp"))
        .filter(|path| path.starts_with(repo_root().join(COMPILED_CPP_DIR)))
        .collect();
    assert!(
        !sources.is_empty(),
        "the shim has .cpp files; a discovery that finds none would run clang-tidy on nothing"
    );

    let args = clang_tidy_arguments(
        std::path::Path::new("/repo"),
        std::path::Path::new("/prefix"),
        std::path::Path::new("/gcc/include"),
        &sources,
    );

    assert_eq!(args[0], "-p");
    assert_eq!(args[1], "/repo");
    for source in &sources {
        assert!(
            args.iter().any(|arg| arg == &source.display().to_string()),
            "{} is not on the command line",
            source.display()
        );
    }
    assert!(args
        .iter()
        .any(|arg| arg == "--header-filter=^/.*/crates/qgis-sys/src/native_manager/.*"));
    assert!(
        args.iter().any(|arg| arg == "--extra-arg=-I/gcc/include"),
        "the GCC internal include dir is missing"
    );
    assert!(
        args.iter().all(|arg| !arg.contains("cxxbridge")),
        "clang-tidy must not depend on a removed cxxbridge binding"
    );
}

/// clang-tidy reads `compile_commands.json`, which `qgis-sys`'s build script
/// writes for the sources cargo compiles. The GoogleTest suite is built by
/// CMake instead, so it is not in that database and must not be handed to
/// clang-tidy — it would fall back to a guessed command line and fail on the
/// first Qt include.
#[test]
fn clang_tidy_skips_the_cpp_suite_the_compile_database_does_not_describe() {
    let formatted: Vec<std::path::PathBuf> = cpp_sources();
    assert!(
        formatted
            .iter()
            .any(|path| path.ends_with("tests/cpp/conversions_test.cpp")),
        "the suite should still be formatted"
    );

    let tidied: Vec<std::path::PathBuf> = formatted
        .into_iter()
        .filter(|path| path.extension().is_some_and(|extension| extension == "cpp"))
        .filter(|path| path.starts_with(repo_root().join(COMPILED_CPP_DIR)))
        .collect();
    assert!(
        tidied
            .iter()
            .all(|path| !path.to_string_lossy().contains("/tests/")),
        "clang-tidy was handed a file the compile database has never seen"
    );
}

#[test]
fn clang_tidy_uses_the_conda_standard_library_and_sysroot() {
    let args = clang_tidy_arguments(
        std::path::Path::new("/repo"),
        std::path::Path::new("/prefix"),
        std::path::Path::new("/gcc/include"),
        &[std::path::PathBuf::from("/shim/application.cpp")],
    );
    for expected in [
        "--extra-arg=--sysroot=/prefix/x86_64-conda-linux-gnu/sysroot",
        "--extra-arg=-nostdinc++",
        "--extra-arg=-isystem/gcc/include/c++",
        "--extra-arg=-isystem/gcc/include/c++/x86_64-conda-linux-gnu",
        "--extra-arg=-isystem/gcc/include/c++/backward",
    ] {
        assert!(args.iter().any(|arg| arg == expected), "no {expected}");
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
        "py-packages/qgis-py/python/qgis_py/_api.py"
    ));
    assert!(looks_like_source(
        "py-packages/qgis-py/python/qgis_py/_transport.py"
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
        "py-packages/qgis-py/python/qgis_py/__pycache__/cli.pyc"
    ));
    assert!(!looks_like_source(
        "py-packages/qgis-py/dist/qgis_py-0.1.0.whl"
    ));
}

#[test]
fn qca_setup_reports_an_already_correct_soname_without_rewriting_it() {
    let lib = std::env::temp_dir().join(format!("xtask-qca-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&lib);
    std::fs::create_dir_all(&lib).expect("create lib dir");
    let source = lib.join("libqca-qt5.so.2.3.12");
    std::fs::write(&source, "library").expect("seed package file");
    std::os::unix::fs::symlink(&source, lib.join("libqca-qt5.so.2")).expect("seed soname");

    assert_eq!(
        setup_qca_in(&lib).expect("inspect soname"),
        QcaRepair::NothingToRepair
    );
    assert_eq!(
        std::fs::read_link(lib.join("libqca-qt5.so.2")).expect("read soname"),
        source
    );
    let _ = std::fs::remove_dir_all(&lib);
}

#[test]
fn qca_setup_repairs_a_missing_soname_from_the_packaged_qt5_library() {
    let lib = std::env::temp_dir().join(format!("xtask-qca-missing-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&lib);
    std::fs::create_dir_all(&lib).expect("create lib dir");
    let source = lib.join("libqca-qt5.so.2.3.12");
    std::fs::write(&source, "library").expect("seed package file");

    assert_eq!(
        setup_qca_in(&lib).expect("repair soname"),
        QcaRepair::Repaired
    );
    assert_eq!(
        std::fs::read_link(lib.join("libqca-qt5.so.2")).expect("read soname"),
        source
    );
    let _ = std::fs::remove_dir_all(&lib);
}

#[test]
fn no_source_file_in_this_repository_is_hidden_from_git() {
    check_sources().expect("every source file is committed or committable");
}
