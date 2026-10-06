---
type: Build
title: Build System
description: How build.rs compiles the native manager with cc and writes compile_commands.json.
status: stable
tags: [build, native-manager, cc, compile-commands]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# Build System

## Overview

The build pipeline has one optional native implementation path:

- The default `qgis` feature makes `crates/qgis-sys/build.rs` compile the native-manager translation unit with `cc`.
- The Pixi C++ feature declares CMake, Ninja, GTest, and RapidCheck for future standalone native targets and tests; the dependency and environment work is tracked in [TASK-24](../backlog/tasks/task-24%20-%20Add-cmake-and-ninja-to-the-C-toolchain-dependencies.md).
- No CXX bridge or per-class shim is built by `qgis-sys`.
- `qgis-sys --no-default-features` skips the native translation unit and
  returns a structured `backend_unavailable` response. `qgis-engine` and
  `qgis-mcp` expose the same split through their `qgis` features.

## Native manager boundary

`crates/qgis-sys/src/native_manager/manager.cpp` is the sole translation unit
that includes QGIS headers. It owns the RFC 19 manager, its registry, and the
JSON codecs; the retired per-class CXX declarations are not part of the build.

The Rust-consumer path compiles the manager into the existing qgis-sys static
archive. `build.rs` applies `-fvisibility=hidden` to the C++ shim compilation,
and `include/native_manager/manager.h` opts only `qgis_invoke`, `qgis_free`, and
`qgis_transport_version` back into default visibility. A future standalone
shared manager target can be modelled with the CMake/Ninja toolchain from
TASK-24; phase 2 proves the same symbol policy and ABI through the Rust consumer
first.

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
| `.h`      | `include/`  | Native-manager C ABI headers |
| `.cpp`    | `src/`      | Native-manager implementation |

The build script discovers the manager translation unit and headers directly;
there is no bridge-generation stage.

## Manager compilation stage

```rust
let mut manager = cc::Build::new();
manager.cpp(true).std("c++17").include("include");
manager.file("src/native_manager/manager.cpp");
```

The manager is compiled as a static archive and linked into the Rust consumer.
`-fvisibility=hidden` is applied to the translation unit, while the three C ABI
declarations in `include/native_manager/manager.h` opt back into default
visibility.

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

## Native application shutdown order

The owner thread constructs a real headless `QgsApplication`, not a base
`QApplication`. Shutdown on that same thread is ordered: release registered layers,
call `QgsApplication::exitQgis()` so providers and process-wide registries stop,
then destroy the `QgsApplication`, and only then let the owner thread exit. The
application must not be leaked past owner-thread exit: Qt thread-local cleanup can
otherwise run after its `QThreadStorage` owner has been destroyed, producing the
intermittent post-test SIGSEGV tracked by TASK-47. The remaining Qt warning that the
application was not created in `main()` describes the accepted dedicated-owner-thread
architecture in D12; it is not permission to move destruction to another thread.

## Rerun Triggers

```rust
cargo:rerun-if-changed=<file>    // for each manager source and header
cargo:rerun-if-env-changed=CONDA_PREFIX
cargo:rerun-if-env-changed=QGIS_INCLUDE_DIR
cargo:rerun-if-env-changed=QT_INCLUDE_DIR
cargo:rerun-if-env-changed=QGIS_LIB_DIR
```
