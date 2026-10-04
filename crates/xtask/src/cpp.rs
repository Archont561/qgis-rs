//! The native manager's own C++ suite: configure, build, run.
//!
//! The Rust integration tests in `crates/qgis-sys/tests/*.rs` exercise the
//! manager through its C ABI with a real QGIS behind it. They cannot reach
//! the conversions on its edges — the JSON envelope, the handle encoding, the
//! malloc/free pair — as units, because loading the manager means starting
//! QGIS. `crates/qgis-sys/tests/cpp` builds those conversions on their own
//! against GoogleTest and RapidCheck, and this module is how the gate runs
//! it: one subcommand, three programs, no shell file (D10).
//!
//! CMake and Ninja are declared in `pixi.toml` for exactly this; GTest,
//! RapidCheck and Qt5 come from the same prefix, which is why the configure
//! step points `CMAKE_PREFIX_PATH` at it rather than trusting a system
//! search path that an airlocked machine does not have.

use std::path::{Path, PathBuf};

use anyhow::{Context, Result};

use crate::util::{repo_root, run};

/// The C++ suite's source directory, relative to the repository root.
pub const CPP_TEST_DIR: &str = "crates/qgis-sys/tests/cpp";

/// Where CMake writes, relative to the repository root.
///
/// Under `target/` on purpose: that is the one directory the repository
/// already ignores wholesale, so a configure run cannot leave files that
/// `check-sources` then reports as source hidden by `.gitignore`.
pub const CPP_TEST_BUILD_DIR: &str = "target/cpp-tests";

/// The CMake configure command line.
///
/// A pure seam, like `clang_tidy_arguments`: `tests/cpp.rs` pins the contract
/// without a compiler, because the thing worth protecting is that the
/// generator and the package prefix stay explicit.
#[must_use]
pub fn configure_arguments(source: &Path, build: &Path, prefix: &Path) -> Vec<String> {
    vec![
        "-S".to_string(),
        source.display().to_string(),
        "-B".to_string(),
        build.display().to_string(),
        "-G".to_string(),
        "Ninja".to_string(),
        format!("-DCMAKE_PREFIX_PATH={}", prefix.display()),
    ]
}

/// The CMake build command line.
#[must_use]
pub fn build_arguments(build: &Path) -> Vec<String> {
    vec!["--build".to_string(), build.display().to_string()]
}

/// The ctest command line.
///
/// `--output-on-failure` because the gate's reader is a log: a failed
/// GoogleTest assertion that only says "1 test failed" names nothing.
#[must_use]
pub fn ctest_arguments(build: &Path) -> Vec<String> {
    vec![
        "--test-dir".to_string(),
        build.display().to_string(),
        "--output-on-failure".to_string(),
    ]
}

/// Build and run the native manager's C++ suite.
///
/// # Errors
///
/// Fails if the pixi prefix is not active, or if any of configure, build or
/// ctest does.
pub fn test_cpp() -> Result<()> {
    let root = repo_root();
    let prefix = std::env::var("CONDA_PREFIX")
        .context("CONDA_PREFIX is not set — run this under `pixi run -e default`")?;
    let source: PathBuf = root.join(CPP_TEST_DIR);
    let build: PathBuf = root.join(CPP_TEST_BUILD_DIR);

    run(
        "cmake",
        configure_arguments(&source, &build, Path::new(&prefix)),
    )?;
    run("cmake", build_arguments(&build))?;
    run("ctest", ctest_arguments(&build))
}
