//! The native manager's C++ suite as the gate reaches it: a CMake configure,
//! a build and a ctest run, each pinned by its argument contract rather than
//! by starting a compiler, plus the discovery that decides which sources the
//! suite is built from.

use std::path::Path;

use xtask::cpp::{
    build_arguments, configure_arguments, ctest_arguments, CPP_TEST_BUILD_DIR, CPP_TEST_DIR,
};
use xtask::util::{cpp_sources, repo_root};

#[test]
fn the_cpp_suite_lives_where_the_runner_looks_for_it() {
    let suite = repo_root().join(CPP_TEST_DIR);
    assert!(
        suite.join("CMakeLists.txt").is_file(),
        "{} has no CMakeLists.txt — the runner would configure nothing",
        suite.display()
    );
    assert!(
        suite
            .read_dir()
            .expect("the suite directory is readable")
            .filter_map(Result::ok)
            .any(|entry| entry.path().extension().is_some_and(|ext| ext == "cpp")),
        "the suite has no .cpp files; a green run would prove nothing"
    );
}

/// The build directory is inside `target/`, which is the one tree the
/// repository already ignores. A build directory that git can see would be
/// reported by `check-sources` the first time CMake wrote a generated header
/// into it.
#[test]
fn the_build_directory_is_inside_the_ignored_target_tree() {
    assert!(
        CPP_TEST_BUILD_DIR.starts_with("target/"),
        "{CPP_TEST_BUILD_DIR} is not under target/, so CMake output would be committed"
    );
}

/// Configure names both directories explicitly, pins Ninja so the generator
/// does not depend on what else is installed, and points CMake's package
/// search at the active pixi prefix — Qt5, GTest and RapidCheck are all
/// there and nowhere else.
#[test]
fn configure_pins_the_generator_and_the_pixi_prefix() {
    let args = configure_arguments(
        Path::new("/repo/crates/qgis-sys/tests/cpp"),
        Path::new("/repo/target/cpp-tests"),
        Path::new("/prefix"),
    );

    assert_eq!(args[0], "-S");
    assert_eq!(args[1], "/repo/crates/qgis-sys/tests/cpp");
    assert_eq!(args[2], "-B");
    assert_eq!(args[3], "/repo/target/cpp-tests");
    assert!(args.iter().any(|arg| arg == "Ninja"));
    assert!(args.iter().any(|arg| arg == "-DCMAKE_PREFIX_PATH=/prefix"));
}

#[test]
fn the_build_and_the_test_run_address_the_same_directory() {
    let build = build_arguments(Path::new("/repo/target/cpp-tests"));
    let ctest = ctest_arguments(Path::new("/repo/target/cpp-tests"));

    assert_eq!(build, vec!["--build", "/repo/target/cpp-tests"]);
    assert_eq!(ctest[0], "--test-dir");
    assert_eq!(ctest[1], "/repo/target/cpp-tests");
    assert!(
        ctest.iter().any(|arg| arg == "--output-on-failure"),
        "a failed C++ assertion that prints nothing is a failure nobody can read"
    );
}

/// The format gate sees the suite too. Before this, `cpp_sources` walked only
/// `src` and `include`, so a test file could be committed unformatted and the
/// drift gate would stay green.
#[test]
fn the_format_gate_covers_the_cpp_suite() {
    let sources = cpp_sources();
    assert!(
        sources
            .iter()
            .any(|path| path.ends_with("tests/cpp/conversions_test.cpp")),
        "the C++ test sources are invisible to check-cpp and format-cpp"
    );
}
