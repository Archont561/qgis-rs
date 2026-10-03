use std::{
    env,
    path::{Path, PathBuf},
};

use anyhow::{Context, Result};
use walkdir::WalkDir;

/// Qt modules required by the native manager's QGIS headers.
const QT_MODULES: &[&str] = &["QtCore", "QtGui", "QtWidgets", "QtXml"];

fn main() -> Result<()> {
    if env::var_os("CARGO_FEATURE_QGIS").is_none() {
        println!("cargo:warning=qgis-sys built without the QGIS backend");
        return Ok(());
    }

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

    // Detect Qt major version from directory name.
    let qt_major = if qt_inc.ends_with("qt6") { 6 } else { 5 };

    // The native manager is the only QGIS implementation. There is no CXX
    // bridge or direct per-class shim to discover or compile here.
    let headers = glob("include", "h")?;
    let shims = glob("src", "cpp")?;

    let mut manager = cc::Build::new();
    manager
        .cpp(true)
        .std("c++17")
        .include("include")
        .include(&qgis_inc)
        .include(&qt_inc);

    for module in QT_MODULES {
        manager.include(qt_inc.join(module));
    }

    manager
        .flag_if_supported("-Wall")
        .flag_if_supported("-Wextra")
        .flag_if_supported("-Werror")
        // The native manager opts its three C ABI declarations back into
        // default visibility; every other manager symbol stays hidden.
        .flag_if_supported("-fvisibility=hidden");

    for file in &shims {
        manager.file(file);
    }

    manager.compile("qgis-sys-shim");

    println!("cargo:rustc-link-search=native={}", qgis_lib.display());
    println!("cargo:rustc-link-lib=dylib=qgis_core");

    for module in QT_MODULES {
        let lib = module.strip_prefix("Qt").unwrap();
        println!("cargo:rustc-link-lib=dylib=Qt{}{}", qt_major, lib);
    }

    println!("cargo:rustc-link-arg=-Wl,-rpath,{}", qgis_lib.display());

    write_compile_commands(&manifest_dir, &qt_inc, &qgis_inc, &shims)?;

    for file in headers.iter().chain(shims.iter()) {
        println!("cargo:rerun-if-changed={file}");
    }
    println!(
        "cargo:rerun-if-changed=native_manager/generated/api_manifest.json"
    );
    println!(
        "cargo:rerun-if-changed=include/native_manager/generated/operation_table.inc"
    );
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
        .filter_map(|entry| entry.ok())
        .filter(|entry| {
            let path = entry.path();
            path.is_file() && path.extension().and_then(|value| value.to_str()) == Some(ext)
        })
        .map(|entry| entry.path().to_string_lossy().into_owned())
        .collect();

    files.sort();
    Ok(files)
}

fn write_compile_commands(
    manifest_dir: &Path,
    qt_inc: &Path,
    qgis_inc: &Path,
    shims: &[String],
) -> Result<()> {
    let workspace_root = manifest_dir
        .parent()
        .context("missing crates/ directory")?
        .parent()
        .context("missing workspace root")?;

    let mut include_dirs = vec![manifest_dir.join("include"), qt_inc.to_path_buf()];
    for module in QT_MODULES {
        include_dirs.push(qt_inc.join(module));
    }
    include_dirs.push(qgis_inc.to_path_buf());

    let flags: String = include_dirs
        .iter()
        .map(|path| format!("-I{}", path.display()))
        .collect::<Vec<_>>()
        .join(" ");

    let entries: Vec<String> = shims
        .iter()
        .map(|file| {
            let absolute = manifest_dir.join(file);
            format!(
                r#"  {{
    "directory": "{}",
    "file": "{}",
    "command": "c++ -std=c++17 {} {}"
  }}"#,
                manifest_dir.display(),
                absolute.display(),
                flags,
                absolute.display(),
            )
        })
        .collect();

    let json = format!("[\n{}\n]\n", entries.join(",\n"));
    std::fs::write(workspace_root.join("compile_commands.json"), json)
        .context("failed to write compile_commands.json")?;

    Ok(())
}
