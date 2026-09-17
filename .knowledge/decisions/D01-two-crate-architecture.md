---
type: Decision
id: D01
title: Two-Crate Architecture
description: "Split into qgis-sys (raw FFI) and qgis (safe wrappers) following the standard -sys crate pattern."
status: draft
tags: [architecture, crate-design, ffi]
date: 2026-09-17T00:00:00Z
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# D01: Two-Crate Architecture

## Decision

Split the project into two crates:

```
crates/
├── qgis-sys/    # raw FFI — CXX bridges, C++ shims, opaque handles
└── qgis/        # safe, idiomatic Rust API
```

## Rationale

Every successful Rust binding to a C/C++ library follows this pattern:

| -sys crate | Safe crate | Library |
|------------|-----------|---------|
| `gdal-sys` | `gdal` | GDAL |
| `openssl-sys` | `openssl` | OpenSSL |
| `raylib-sys` | `raylib` | Raylib |
| `librebound-sys` | `rebound` | REBOUND |
| `qgis-sys` | `qgis` | QGIS |

The `-sys` crate is **mechanical**: one function signature in, one function call out. No opinions, no safety, no ergonomics. It maps 1:1 to the C++ API.

The safe crate is where **all the hard decisions live**:
- Ownership contracts (who deletes what)
- Error types (QgsError → `Result<T, QgisError>`)
- Iterators (QgsFeatureIterator → `impl Iterator<Item = Feature>`)
- Builders (layer creation options)
- RAII wrappers (scope guards for editing transactions)
- Rust-idiomatic naming (`feature_count()` not `vector_layer_feature_count()`)

## What Changes

### qgis-sys (existing)
- Keep as-is: opaque handles, CXX bridges, C++ shims
- Add more types mechanically via scaffold
- No safe abstractions — raw FFI only

### qgis (new)
- `crates/qgis/Cargo.toml` depends on `qgis-sys`
- Re-exports safe wrappers: `qgis::VectorLayer`, `qgis::Application`, etc.
- `#![forbid(unsafe_code)]` — all unsafe is contained in qgis-sys
- Error type: `QgisError` with structured variants
- Builder pattern for constructors
- RAII guards for scoped operations

## Consequences

- Users add `qgis` to `Cargo.toml`, never `qgis-sys` directly
- qgis-sys becomes an implementation detail
- Safe crate can evolve independently (semver-friendly)
- Unsafe code is auditable in one crate
