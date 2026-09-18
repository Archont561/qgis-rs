---
type: Context
title: Project Context
description: Orientation file for AI agents and contributors working on qgis-rs.
status: stable
tags: [project, orientation, agents]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# qgis-rs — Project Context

## What This Is

**qgis-rs** is a Rust binding library for the [QGIS](https://qgis.org) C++ geospatial API.
It uses the [cxx](https://cxx.rs) crate to provide safe, zero-cost FFI between Rust and the QGIS C++ core — without hand-written `extern "C"` wrappers or `bindgen` output.

The long-term goal is a safe, idiomatic Rust API that exposes QGIS's vector/raster layers, coordinate reference systems, geometry operations, symbology, and map rendering.

## Core Constraints

- **CXX-only FFI** — no raw `extern "C"` blocks, no `bindgen`. Every C++ call goes through a `#[cxx::bridge]`.
- **Opaque handle pattern** — QGIS objects are wrapped in lightweight `void*`-carrying handles declared with `QGIS_DECLARE_HANDLE` and destroyed via `QGIS_DEFINE_HANDLE_DTOR`.
- **Qt dependency** — QGIS depends on Qt (currently Qt5 or Qt6 via conda-forge). The build detects the Qt major version automatically.
- **GPL-2.0-or-later license** — inherited from QGIS.

## Toolchain

| Action      | Command                            | Notes                                              |
|-------------|------------------------------------|----------------------------------------------------|
| Bootstrap   | `sh scripts/setup-env.sh`          | Clone env pack + install (when pixi unavailable)   |
| Activate    | `. scripts/use-pack.sh`            | Put pack tools on PATH + set CONDA_PREFIX          |
| Environment | `pixi shell`                       | Activates conda-forge env with rust, clang, QGIS   |
| Build       | `cargo build -p qgis-sys`          | Compiles bridges + C++ shims via build.rs          |
| Format      | `cargo fmt --all`                  | Rust formatting (C++: `clang-format -i`)           |
| Lint        | `cargo clippy --workspace --all-targets -- -D warnings` | Rust lint (C++: `clang-tidy`)      |
| Test        | `pixi run test`                    | Runs integration tests (requires `setup` symlink)  |
| Test (full) | `pixi run test-full`               | Includes vector_layer + application_lifecycle      |
| CI          | `pixi run gates`                   | fmt-check + clippy + test (`ci` adds the C++ format check) |
| Scaffold    | `pixi run scaffold <layer> <concept> <class> <short>` | Generates header + bridge + cpp + mod.rs |

> **When pixi is unavailable** (sandboxed environments), bootstrap via
> `scripts/setup-env.sh` + `. scripts/use-pack.sh`. See [env-provisioning.md](/env-provisioning.md).

## Judgment Boundaries

**NEVER**
- Include QGIS headers in `.h` files — only in `.cpp` shims.
- Use `bindgen` or raw `extern "C"` blocks.
- Commit `compile_commands.json` (gitignored).
- Run tests without `QT_QPA_PLATFORM=offscreen` (will hang on headless CI).

**ASK**
- Before adding a new Qt module to `QT_MODULES` in `build.rs`.
- Before changing the handle macro definitions (`handle.h`).
- Before modifying the `scaffold` task template.

**ALWAYS**
- Wrap all C++ shim functions in `try/catch` returning safe defaults.
- Use `QGIS_NULL_GUARD` to check handle validity before access.
- Declare FFI functions as `noexcept` in both header and bridge.
- Keep `.h` headers free of QGIS-specific includes.

## Skills & Scaffolding

New QGIS types are added via the scaffold task:

```bash
pixi run scaffold core geometry QgsGeometry geometry
```

This generates `include/core/geometry.h`, `src/core/geometry/geometry.{rs,cpp}`, and `src/core/geometry/mod.rs`, then wires them into the module tree and `lib.rs` re-exports.

See [scaffold.md](/scaffold.md) for full details.

## Context Map

```
qgis-rs/
├── Cargo.toml                # workspace root
├── pixi.toml                 # pixi env + tasks + scaffold generator
├── crates/
│   └── qgis-sys/             # the -sys crate (low-level FFI)
│       ├── build.rs          # cxx-build + cc shim + compile_commands.json
│       ├── include/          # CXX-facing headers (no QGIS includes)
│       │   └── core/
│       │       ├── handle.h          # opaque handle macros
│       │       ├── convert.h         # QString ↔ rust::String helpers
│       │       ├── application.h
│       │       ├── application_info.h
│       │       └── vector_layer.h
│       ├── src/
│       │   ├── lib.rs        # re-exports ffi modules as *_ffi
│       │   └── core/
│       │       ├── application/      # QgsApplication shim
│       │       └── vector_layer/     # QgsVectorLayer shim
│       └── tests/            # integration tests (require conda env)
│           ├── fixtures/points.gpkg  # GeoPackage test data
│           └── helpers/mod.rs        # AppHandle RAII wrapper
└── .knowledge/               # this knowledge bundle
```
