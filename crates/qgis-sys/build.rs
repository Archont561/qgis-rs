use std::{env, path::PathBuf};

use anyhow::{Context, Result};
use walkdir::WalkDir;

/// Qt modules required by QGIS headers.
/// Add new modules here as the compiler asks for them.
const QT_MODULES: &[&str] = &["QtCore", "QtGui", "QtWidgets", "QtXml"];

fn main() -> Result<()> {
    let out_dir = PathBuf::from(env::var("OUT_DIR")?);
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR")?);

    let conda = env::var("CONDA_PREFIX")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/usr"));

    let qgis_inc = env::var("QGIS_INCLUDE_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| conda.join("include/qgis"));

    // Qt5 on conda-forge: include/qt   Qt6: include/qt6
    let qt_inc = env::var("QT_INCLUDE_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            let qt5 = conda.join("include/qt");
            let qt6 = conda.join("include/qt6");
            if qt5.exists() {
                qt5
            } else {
                qt6
            }
        });

    let qgis_lib = env::var("QGIS_LIB_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| conda.join("lib"));

    // Detect Qt major version from directory name
    let qt_major = if qt_inc.ends_with("qt6") { 6 } else { 5 };

    // ── Discover files ────────────────────────────────────────────────────
    let bridges = glob("src", "rs")?;
    let headers = glob("include", "h")?;
    let shims = glob("src", "cpp")?;

    // ── CXX bridge ───────────────────────────────────────────────────────
    cxx_build::bridges(&bridges)
        .std("c++17")
        .include("include")
        .compile("qgis-sys-cxx");

    let cxxbridge_include = out_dir.join("cxxbridge/include");
    let cxxbridge_crate = out_dir.join("cxxbridge/crate");

    // ── Shim archive ─────────────────────────────────────────────────────
    let mut shim = cc::Build::new();
    shim.cpp(true)
        .std("c++17")
        .include("include")
        .include(&cxxbridge_include)
        .include(&cxxbridge_crate)
        .include(&qgis_inc)
        .include(&qt_inc);

    for module in QT_MODULES {
        shim.include(qt_inc.join(module));
    }

    shim.flag_if_supported("-Wall")
        .flag_if_supported("-Wextra")
        .flag_if_supported("-Werror");

    for f in &shims {
        shim.file(f);
    }

    shim.compile("qgis-sys-shim");

    // ── Link ──────────────────────────────────────────────────────────────
    println!("cargo:rustc-link-search=native={}", qgis_lib.display());
    println!("cargo:rustc-link-lib=dylib=qgis_core");

    for module in QT_MODULES {
        let lib = module.strip_prefix("Qt").unwrap();
        println!("cargo:rustc-link-lib=dylib=Qt{}{}", qt_major, lib);
    }

    println!("cargo:rustc-link-arg=-Wl,-rpath,{}", qgis_lib.display());

    // ── compile_commands.json for clangd ──────────────────────────────────
    write_compile_commands(
        &manifest_dir,
        &cxxbridge_include,
        &cxxbridge_crate,
        &qt_inc,
        &qgis_inc,
        &shims,
    )?;

    // ── Rerun triggers ───────────────────────────────────────────────────
    for f in bridges.iter().chain(headers.iter()).chain(shims.iter()) {
        println!("cargo:rerun-if-changed={f}");
    }
    println!("cargo:rerun-if-env-changed=CONDA_PREFIX");
    println!("cargo:rerun-if-env-changed=QGIS_INCLUDE_DIR");
    println!("cargo:rerun-if-env-changed=QT_INCLUDE_DIR");
    println!("cargo:rerun-if-env-changed=QGIS_LIB_DIR");

    Ok(())
}

fn glob(dir: &str, ext: &str) -> Result<Vec<String>> {
    if !std::path::Path::new(dir).exists() {
        return Ok(vec![]);
    }

    let mut files: Vec<String> = WalkDir::new(dir)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| {
            let p = e.path();
            let name = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
            p.is_file()
                && p.extension().and_then(|x| x.to_str()) == Some(ext)
                && name != "lib.rs"
                && name != "mod.rs"
        })
        .map(|e| e.path().to_string_lossy().into_owned())
        .collect();

    files.sort();
    Ok(files)
}

fn write_compile_commands(
    manifest_dir: &PathBuf,
    cxxbridge_include: &PathBuf,
    cxxbridge_crate: &PathBuf,
    qt_inc: &PathBuf,
    qgis_inc: &PathBuf,
    shims: &[String],
) -> Result<()> {
    let workspace_root = manifest_dir
        .parent()
        .context("missing crates/ directory")?
        .parent()
        .context("missing workspace root")?;

    let mut include_dirs = vec![
        manifest_dir.join("include"),
        cxxbridge_include.clone(),
        cxxbridge_crate.clone(),
        qt_inc.clone(),
    ];

    for module in QT_MODULES {
        include_dirs.push(qt_inc.join(module));
    }

    include_dirs.push(qgis_inc.clone());

    let flags: String = include_dirs
        .iter()
        .map(|p| format!("-I{}", p.display()))
        .collect::<Vec<_>>()
        .join(" ");

    let entries: Vec<String> = shims
        .iter()
        .map(|f| {
            let abs = manifest_dir.join(f);
            format!(
                r#"  {{
    "directory": "{}",
    "file": "{}",
    "command": "c++ -std=c++17 {} {}"
  }}"#,
                manifest_dir.display(),
                abs.display(),
                flags,
                abs.display(),
            )
        })
        .collect();

    let json = format!("[\n{}\n]\n", entries.join(",\n"));

    std::fs::write(workspace_root.join("compile_commands.json"), json)
        .context("failed to write compile_commands.json")?;

    Ok(())
}
