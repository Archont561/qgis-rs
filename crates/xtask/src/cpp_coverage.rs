//! GCC coverage of the native manager, separate from ordinary builds and gates.

use anyhow::{bail, Context, Result};
use serde::Deserialize;

/// Minimum line coverage of the QGIS-free conversions, enforced without rounding.
pub const CONVERSIONS_LINE_MIN: u64 = 95;

const CONVERSIONS: &str = "crates/qgis-sys/src/native_manager/conversions.cpp";
const MANAGER: &str = "crates/qgis-sys/src/native_manager/manager.cpp";

#[derive(Deserialize)]
struct Summary {
    files: Vec<FileSummary>,
}

#[derive(Deserialize)]
struct FileSummary {
    filename: String,
    line_total: u64,
    line_covered: u64,
}

/// Validate a gcovr JSON summary at the report boundary.
///
/// Public so integration tests can prove missing, empty, or below-threshold
/// production coverage cannot masquerade as a successful measurement.
///
/// # Errors
/// Rejects malformed summaries, missing production files, or insufficient coverage.
pub fn validate_summary(json: &str) -> Result<()> {
    let summary: Summary = serde_json::from_str(json).context("invalid gcovr summary")?;
    for path in [CONVERSIONS, MANAGER] {
        let files: Vec<_> = summary
            .files
            .iter()
            .filter(|file| file.filename == path)
            .collect();
        if files.len() != 1 {
            bail!("native coverage requires exactly one {path} row");
        }
        let file = files[0];
        if file.line_total == 0 || file.line_covered == 0 || file.line_covered > file.line_total {
            bail!("{path} has invalid or unexecuted line coverage");
        }
        if path == CONVERSIONS
            && u128::from(file.line_covered) * 100
                < u128::from(file.line_total) * u128::from(CONVERSIONS_LINE_MIN)
        {
            bail!(
                "{path} is below {CONVERSIONS_LINE_MIN}% line coverage: {}/{}",
                file.line_covered,
                file.line_total
            );
        }
    }
    Ok(())
}

/// Instrument, execute, merge and validate native coverage offline.
///
/// # Errors
/// Fails on a missing tool, failed suite, gcov error, or invalid coverage report.
pub fn run() -> Result<()> {
    use crate::util::{repo_root, run, step};
    use std::{fs, path::Path};
    let root = repo_root();
    let prefix = std::env::var("CONDA_PREFIX").context("run under pixi default")?;
    let build = root.join("target/cpp-coverage");
    // Clean only this producer's private tree: stale counters must not inflate
    // a subsequent measurement, nor invalidate the normal Cargo/CMake caches.
    if build.exists() {
        fs::remove_dir_all(&build)?;
    }
    fs::create_dir_all(&build)?;
    let reports = root.join("target/coverage");
    fs::create_dir_all(&reports)?;
    for name in ["native.xml", "native-summary.json", "native.json"] {
        let path = reports.join(name);
        if path.exists() {
            fs::remove_file(path)?;
        }
    }
    step("instrumented conversions suite");
    let cmake = build.join("cmake");
    let mut args = crate::cpp::configure_arguments(
        &root.join(crate::cpp::CPP_TEST_DIR),
        &cmake,
        Path::new(&prefix),
    );
    args.extend([
        "-DCMAKE_CXX_COMPILER=g++".into(),
        "-DCMAKE_CXX_FLAGS=--coverage -O0 -g".into(),
        "-DCMAKE_EXE_LINKER_FLAGS=--coverage".into(),
    ]);
    run("cmake", args)?;
    run("cmake", crate::cpp::build_arguments(&cmake))?;
    run("ctest", crate::cpp::ctest_arguments(&cmake))?;
    step("instrumented native manager through QGIS Rust tests");
    let status = native_test_command(&root)
        .status()
        .context("cannot run instrumented native tests")?;
    if !status.success() {
        bail!("instrumented native tests failed: {status}");
    }
    step("merge native profiles");
    run(
        "gcovr",
        vec![
            "--root".into(),
            root.display().to_string(),
            "--gcov-executable".into(),
            "gcov".into(),
            "--filter".into(),
            "crates/qgis-sys/src/native_manager/.*".into(),
            "--filter".into(),
            "crates/qgis-sys/include/native_manager/.*".into(),
            "--merge-mode-functions".into(),
            "merge-use-line-min".into(),
            "--xml".into(),
            reports.join("native.xml").display().to_string(),
            "--json-summary".into(),
            reports.join("native-summary.json").display().to_string(),
            "--json".into(),
            reports.join("native.json").display().to_string(),
            build.display().to_string(),
        ],
    )?;
    validate_summary(&fs::read_to_string(reports.join("native-summary.json"))?)?;
    println!(
        "native coverage: {}",
        fs::read_to_string(reports.join("native-summary.json"))?
    );
    Ok(())
}

/// Build the offline native-test invocation without executing it.
///
/// Public for consumer-side command-contract tests: instrumentation and private
/// output paths must survive changes to the coverage orchestrator.
#[must_use]
pub fn native_test_command(root: &std::path::Path) -> std::process::Command {
    let mut command = std::process::Command::new("cargo");
    command
        .args([
            "nextest",
            "run",
            "--offline",
            "-p",
            "qgis-sys",
            "-p",
            "qgis-mcp",
            "--features",
            "qgis-sys/qgis,qgis-mcp/qgis",
            "--test-threads=1",
        ])
        .current_dir(root)
        .env("CARGO_TARGET_DIR", root.join("target/cpp-coverage/cargo"))
        .env("CARGO_NET_OFFLINE", "true")
        .env("CARGO_PROFILE_DEV_DEBUG", "0")
        .env("CARGO_PROFILE_TEST_DEBUG", "0")
        .env("CXX", "g++")
        .env("CXXFLAGS", "--coverage -O0 -g -fprofile-update=atomic")
        .env("RUSTFLAGS", "-C link-arg=-lgcov")
        .env("QT_QPA_PLATFORM", "offscreen");
    command
}
