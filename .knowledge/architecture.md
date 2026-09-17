---
type: Architecture
title: Architecture
description: Crate layout, layer model, and FFI data flow for qgis-rs.
status: stable
tags: [architecture, crate, ffi, layers]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# Architecture

## Crate Model

The workspace follows the standard Rust `-sys` crate pattern:

| Crate        | Purpose                                                  |
|--------------|----------------------------------------------------------|
| `qgis-sys`   | Low-level FFI bindings — opaque handles, C++ shims, CXX bridges |
| *(future)* `qgis` | Safe, idiomatic Rust wrappers on top of `qgis-sys`  |

## Layer Organization

Inside `qgis-sys`, code is organized by **QGIS module layer**:

```
src/
├── lib.rs            # module tree root + ffi re-exports
└── core/             # maps to QGIS "core" library (libqgis_core)
    ├── application/  # QgsApplication, app info
    ├── vector_layer/ # QgsVectorLayer
    ├── geometry/     # (future) QgsGeometry
    └── ...
```

Each concept directory contains:
- `mod.rs` — Rust module declaration
- `<short>.rs` — `#[cxx::bridge]` with FFI signatures
- `<short>.cpp` — C++ implementation (includes real QGIS headers)

## FFI Data Flow

```
Rust caller
  │
  ▼
#[cxx::bridge] ──► generated CXX glue (target/debug/build/.../cxxbridge/)
  │                    │
  │                    ▼
  │              C++ shim function (src/core/.../<short>.cpp)
  │                    │
  │                    ▼
  └──────────────► QGIS C++ API (via conda-forge headers)
```

### Key Invariants

1. **Headers are clean** — `include/core/*.h` never include QGIS headers. They only declare opaque handles and function signatures.
2. **Shims contain the danger** — `src/core/.../*.cpp` includes real QGIS headers and implements the bridge. All exceptions are caught here.
3. **Bridges are the contract** — `src/core/.../*.rs` defines the exact CXX bridge. The CXX compiler statically verifies that Rust signatures match C++ declarations.

## Namespace Convention

All C++ code lives under `qgis_shim::<layer>`, e.g.:
- `qgis_shim::core` — core layer shims

This prevents symbol collisions and gives each layer its own scope.

## Handle Pattern

QGIS C++ objects are never exposed by value. Instead:

1. **Header** declares `QGIS_DECLARE_HANDLE(FooHandle)` → a struct with `void* ptr`
2. **C++ shim** defines `QGIS_DEFINE_HANDLE_DTOR(ns, FooHandle, ::QgsFoo)` → destructor calls `delete`
3. **C++ shim** uses `QGIS_HANDLE_CAST(ns::FooHandle, ::QgsFoo)` → provides `real()` / `real_const()` helpers
4. **Rust bridge** sees `FooHandle` as an opaque CXX type, held via `UniquePtr<FooHandle>`

See [ffishim.md](/ffishim.md) for the full pattern with code examples.

## Re-Export Strategy

`lib.rs` re-exports each bridge module under a short alias:

```rust
pub use core::application::app::ffi as application_ffi;
pub use core::vector_layer::layer::ffi as vector_layer_ffi;
```

This lets tests and downstream crates write:
```rust
use qgis_sys::vector_layer_ffi as layer_ffi;
```
