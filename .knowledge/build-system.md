---
type: Build
title: Build System
description: How build.rs orchestrates cxx-build, cc shim compilation, and compile_commands.json.
status: stable
tags: [build, cxx-build, cc, compile-commands]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# Build System

## Overview

The build pipeline in `crates/qgis-sys/build.rs` has three stages:

1. **CXX bridge generation** — `cxx_build::bridges()` generates C++ code from `#[cxx::bridge]` modules
2. **Shim compilation** — `cc::Build` compiles the hand-written C++ shim files
3. **Linking** — `println!("cargo:rustc-link-lib=...")` links against `libqgis_core` and Qt

## Path Discovery

The build script discovers paths in this priority order:

| Variable            | Default (from `CONDA_PREFIX`)           |
|---------------------|-----------------------------------------|
| `CONDA_PREFIX`      | `/usr`                                  |
| `QGIS_INCLUDE_DIR`  | `$CONDA_PREFIX/include/qgis`            |
| `QT_INCLUDE_DIR`    | `$CONDA_PREFIX/include/qt` or `qt6`     |
| `QGIS_LIB_DIR`      | `$CONDA_PREFIX/lib`                     |

Qt major version is detected from the directory name (`qt6` → Qt6, `qt` → Qt5).

## File Discovery

The build script uses `walkdir` to glob for source files:

| Extension | Directory   | Purpose                      |
|-----------|-------------|------------------------------|
| `.rs`     | `src/`      | CXX bridge modules           |
| `.h`      | `include/`  | Public headers               |
| `.cpp`    | `src/`      | C++ shim implementations     |

Files named `lib.rs` and `mod.rs` are excluded from bridge discovery.

## CXX Bridge Stage

```rust
cxx_build::bridges(&bridges)
    .std("c++17")
    .include("include")
    .compile("qgis-sys-cxx");
```

This generates C++ code in `OUT_DIR/cxxbridge/` with two subdirectories:
- `cxxbridge/include/` — generated headers (`rust/cxx.h`, type declarations)
- `cxxbridge/crate/` — generated `.cpp` files implementing the Rust side

## Shim Compilation Stage

```rust
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
```

The shim is compiled as a static archive `libqgis-sys-shim.a` and linked into the final binary.

## Linking

```rust
println!("cargo:rustc-link-lib=dylib=qgis_core");
for module in QT_MODULES {
    let lib = module.strip_prefix("Qt").unwrap();
    println!("cargo:rustc-link-lib=dylib=Qt{}{}", qt_major, lib);
}
println!("cargo:rustc-link-arg=-Wl,-rpath,{}", qgis_lib.display());
```

Current Qt modules: `QtCore`, `QtGui`, `QtWidgets`, `QtXml`.

## compile_commands.json

The build script generates `compile_commands.json` at the workspace root for clangd/clang-tidy integration. This file is gitignored.

## Rerun Triggers

```rust
cargo:rerun-if-changed=<file>    // for each bridge, header, and shim
cargo:rerun-if-env-changed=CONDA_PREFIX
cargo:rerun-if-env-changed=QGIS_INCLUDE_DIR
cargo:rerun-if-env-changed=QT_INCLUDE_DIR
cargo:rerun-if-env-changed=QGIS_LIB_DIR
```
