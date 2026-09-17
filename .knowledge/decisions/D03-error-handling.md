---
type: Decision
id: D03
title: "Error Handling — Structured Results"
description: "Structured Result types with QgsError side-channel instead of silent defaults from noexcept shims."
status: draft
tags: [error-handling, result, qgs-error]
date: 2026-09-17T00:00:00Z
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# D03: Error Handling — Structured Results

## The Problem

Currently, every C++ shim function catches all exceptions and returns a safe default:

```cpp
bool vector_layer_is_valid(const QgsVectorLayerHandle& handle) noexcept {
    try {
        return real_const(handle)->isValid();
    } catch (...) {
        return false;  // ← WHY is it invalid? Unknown.
    }
}
```

The Rust caller gets `false` but has no idea whether the file wasn't found, the format was wrong, the CRS was unknown, or the provider crashed. QGIS actually tracks this — `QgsVectorLayer::error()` returns a `QgsError` with a message and summary — but the shim throws it away.

## Decision

### qgis-sys level: keep noexcept, add error accessors

The noexcept/catch-all pattern stays — exceptions cannot cross FFI. But add a **side-channel** for error retrieval:

```cpp
// New shim function
rust::String vector_layer_error(const QgsVectorLayerHandle& handle) noexcept;
```

```rust
// In the bridge
fn vector_layer_error(handle: &QgsVectorLayerHandle) -> String;
```

This reads `QgsVectorLayer::error().message()` and returns it as a Rust string. Empty string = no error.

### qgis crate level: Result everywhere

```rust
pub enum QgisError {
    /// Layer could not be opened or is invalid
    InvalidLayer { uri: String, message: String },
    /// CRS operation failed
    CrsError(String),
    /// Feature iteration error
    IterationError(String),
    /// QGIS threw an uncaught C++ exception
    CppException(String),
    /// Operation not permitted in current state
    InvalidState(String),
}

impl VectorLayer {
    pub fn open(uri: &str, name: &str, provider: &str) -> Result<Self, QgisError> {
        let inner = ffi::vector_layer_new(uri, name, provider);
        if inner.is_null() {
            return Err(QgisError::InvalidLayer {
                uri: uri.into(),
                message: "FFI returned null".into(),
            });
        }
        if !ffi::vector_layer_is_valid(&inner) {
            let msg = ffi::vector_layer_error(&inner);
            return Err(QgisError::InvalidLayer {
                uri: uri.into(),
                message: msg,
            });
        }
        Ok(Self { inner })
    }
}
```

### Pattern: check-then-extract

```rust
// The safe wrapper checks validity immediately after creation:
let layer = VectorLayer::open("data.gpkg", "points", "ogr")
    .expect("failed to open layer");

// This surfaces the REAL error message:
// QgisError::InvalidLayer {
//     uri: "data.gpkg",
//     message: "Could not open data source 'data.gpkg' with OGR provider"
// }
```

## Consequences

- Every qgis-sys shim that creates or loads objects needs a corresponding `_error()` accessor
- The safe crate checks validity eagerly and returns `Result`
- `QgisError` implements `std::error::Error` and `Display`
- Downstream code uses `?` propagation naturally
