//! Generate the four files a new qgis-sys binding always needs — header, cxx
//! bridge, C++ shim, module wiring — and hook them into the parent `mod.rs`
//! and `lib.rs`.
//!
//! Usage: `pixi run xtask scaffold core geometry QgsGeometry geometry`

use std::fs;
use std::path::Path;

use anyhow::{bail, Context, Result};

use crate::util::repo_root;

/// The crate every generated file belongs to.
const CRATE: &str = "crates/qgis-sys";

/// Scaffold one binding.
pub fn binding(layer: &str, concept: &str, qgis_class: &str, short_name: &str) -> Result<()> {
    let root = repo_root();
    let crate_dir = root.join(CRATE);
    let handle = format!("{qgis_class}Handle");
    let module_dir = crate_dir.join("src").join(layer).join(concept);
    let bridge = module_dir.join(format!("{short_name}.rs"));

    // Refuse rather than overwrite: the generated files are a starting point
    // that gets edited immediately, and regenerating over an edited binding
    // would delete the work without saying so.
    if bridge.exists() {
        bail!(
            "refusing to overwrite existing binding: {}",
            bridge.display()
        );
    }
    fs::create_dir_all(&module_dir)
        .with_context(|| format!("cannot create {}", module_dir.display()))?;

    let header_dir = crate_dir.join("include").join(layer);
    fs::create_dir_all(&header_dir)
        .with_context(|| format!("cannot create {}", header_dir.display()))?;
    let header = header_dir.join(format!("{concept}.h"));
    write(&header, &header_source(layer, concept, short_name, &handle))?;
    write(&bridge, &bridge_source(layer, concept, &handle))?;
    write(
        &module_dir.join(format!("{short_name}.cpp")),
        &shim_source(layer, concept, qgis_class, &handle),
    )?;
    write(
        &module_dir.join("mod.rs"),
        &format!("pub mod {short_name};\n"),
    )?;

    append_once(
        &crate_dir.join("src").join(layer).join("mod.rs"),
        &format!("pub mod {concept};"),
        &format!("pub mod {concept};\n"),
    )?;
    append_once(
        &crate_dir.join("src").join("lib.rs"),
        &format!("{short_name}_ffi"),
        &format!("pub use {layer}::{concept}::{short_name}::ffi as {short_name}_ffi;\n"),
    )?;

    println!(
        "\n✅ scaffolded {layer}/{concept}\n   \
         header:  {CRATE}/include/{layer}/{concept}.h\n   \
         bridge:  {CRATE}/src/{layer}/{concept}/{short_name}.rs\n   \
         shim:    {CRATE}/src/{layer}/{concept}/{short_name}.cpp\n   \
         mod:     {CRATE}/src/{layer}/{concept}/mod.rs\n\n\
         Next steps:\n  \
         1. Edit the header — declare FFI functions\n  \
         2. Edit the .rs    — declare matching Rust signatures\n  \
         3. Edit the .cpp   — implement the functions\n  \
         4. pixi run -e default cargo build -p qgis-sys"
    );
    Ok(())
}

fn write(path: &Path, contents: &str) -> Result<()> {
    fs::write(path, contents).with_context(|| format!("cannot write {}", path.display()))
}

/// Append a line to a file unless something matching `marker` is already in it.
///
/// The parent `mod.rs` and `lib.rs` accumulate one line per binding; running
/// the scaffolder twice for the same concept must not duplicate them.
pub fn append_once(path: &Path, marker: &str, line: &str) -> Result<()> {
    let existing = fs::read_to_string(path).unwrap_or_default();
    if existing.contains(marker) {
        return Ok(());
    }
    let mut updated = existing;
    if !updated.is_empty() && !updated.ends_with('\n') {
        updated.push('\n');
    }
    updated.push_str(line);
    write(path, &updated)
}

pub fn header_source(layer: &str, concept: &str, short_name: &str, handle: &str) -> String {
    format!(
        "#pragma once\n\n\
         #include \"rust/cxx.h\"\n\
         #include \"qgis-sys/include/core/handle.h\"\n\n\
         namespace qgis_shim::{layer} {{\n\n\
         QGIS_DECLARE_HANDLE({handle});\n\n\
         }} // namespace qgis_shim::{layer}\n\n\
         #include \"qgis-sys/src/{layer}/{concept}/{short_name}.rs.h\"\n\n\
         namespace qgis_shim::{layer} {{\n\n\
         // TODO: declare FFI functions here\n\n\
         }} // namespace qgis_shim::{layer}\n"
    )
}

pub fn bridge_source(layer: &str, concept: &str, handle: &str) -> String {
    format!(
        "#[cxx::bridge(namespace = \"qgis_shim::{layer}\")]\n\
         pub mod ffi {{\n    \
         unsafe extern \"C++\" {{\n        \
         include!(\"qgis-sys/include/{layer}/{concept}.h\");\n\n        \
         type {handle};\n\n        \
         // TODO: declare FFI functions here\n    \
         }}\n\
         }}\n"
    )
}

pub fn shim_source(layer: &str, concept: &str, qgis_class: &str, handle: &str) -> String {
    format!(
        "#include \"qgis-sys/include/{layer}/{concept}.h\"\n\
         #include \"qgis-sys/include/core/convert.h\"\n\n\
         // TODO: #include <qgs....h>\n\n\
         // QGIS_DEFINE_HANDLE_DTOR(qgis_shim::{layer}, {handle}, ::{qgis_class})\n\n\
         namespace {{\n\n\
         // QGIS_HANDLE_CAST(qgis_shim::{layer}::{handle}, ::{qgis_class})\n\n\
         }} // namespace\n\n\
         namespace qgis_shim::{layer} {{\n\n\
         // TODO: implement FFI functions here\n\n\
         }} // namespace qgis_shim::{layer}\n"
    )
}
