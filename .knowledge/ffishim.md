---
type: Pattern
title: FFI Shim Pattern
description: The opaque-handle CXX bridge pattern used to wrap every QGIS C++ type.
status: stable
tags: [ffi, cxx, handle, pattern, shim]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# FFI Shim Pattern

Every QGIS type bound to Rust follows the same three-file pattern: a **header**, a **Rust bridge**, and a **C++ shim**.

## 1. Header (`include/<layer>/<concept>.h`)

Declares the opaque handle and function signatures. **Never includes QGIS headers.**

```cpp
#pragma once

#include "rust/cxx.h"
#include "qgis-sys/include/core/handle.h"

namespace qgis_shim::core {

QGIS_DECLARE_HANDLE(QgsVectorLayerHandle);

} // namespace qgis_shim::core

#include "qgis-sys/src/core/vector_layer/layer.rs.h"

namespace qgis_shim::core {

::std::unique_ptr<QgsVectorLayerHandle> vector_layer_new(
    rust::Str uri, rust::Str name, rust::Str provider) noexcept;

bool vector_layer_is_valid(const QgsVectorLayerHandle& handle) noexcept;
rust::String vector_layer_name(const QgsVectorLayerHandle& handle) noexcept;

} // namespace qgis_shim::core
```

### Handle Macros (`handle.h`)

| Macro                    | Purpose                                           |
|--------------------------|---------------------------------------------------|
| `QGIS_DECLARE_HANDLE(N)` | Declares a struct with `void* ptr` and destructor |
| `QGIS_DEFINE_HANDLE_DTOR(ns, N, T)` | Defines the destructor as `delete static_cast<T*>(ptr)` |
| `QGIS_HANDLE_CAST(H, T)` | Provides `real(h)` and `real_const(h)` helpers    |
| `QGIS_NULL_GUARD(h, def)` | Returns `def` early if `h.ptr == nullptr`         |

## 2. Rust Bridge (`src/<layer>/<concept>/<short>.rs`)

Defines the CXX bridge with matching signatures:

```rust
#[cxx::bridge(namespace = "qgis_shim::core")]
pub mod ffi {
    unsafe extern "C++" {
        include!("qgis-sys/include/core/vector_layer.h");

        type QgsVectorLayerHandle;

        fn vector_layer_new(
            uri: &str, name: &str, provider: &str,
        ) -> UniquePtr<QgsVectorLayerHandle>;

        fn vector_layer_is_valid(handle: &QgsVectorLayerHandle) -> bool;
        fn vector_layer_name(handle: &QgsVectorLayerHandle) -> String;
    }
}
```

### Type Mapping

| Rust type          | C++ type           | Notes                    |
|--------------------|--------------------|--------------------------|
| `&str`             | `rust::Str`        | Borrowed UTF-8 string    |
| `String`           | `rust::String`     | Owned string             |
| `bool`             | `bool`             | Direct mapping           |
| `i64`              | `int64_t`          | Direct mapping           |
| `UniquePtr<T>`     | `unique_ptr<T>`    | Owned opaque handle      |
| `&T`               | `const T&`         | Borrowed reference       |
| `Pin<&mut T>`      | `T&`               | Mutable pinned reference |

## 3. C++ Shim (`src/<layer>/<concept>/<short>.cpp`)

Implements the functions using real QGIS types. **This is the only file that includes QGIS headers.**

```cpp
#include "qgis-sys/include/core/vector_layer.h"
#include "qgis-sys/include/core/convert.h"

#include <qgsvectorlayer.h>  // ← real QGIS header

QGIS_DEFINE_HANDLE_DTOR(qgis_shim::core, QgsVectorLayerHandle, ::QgsVectorLayer)

namespace {
QGIS_HANDLE_CAST(qgis_shim::core::QgsVectorLayerHandle, ::QgsVectorLayer)
} // namespace

namespace qgis_shim::core {

::std::unique_ptr<QgsVectorLayerHandle> vector_layer_new(
    rust::Str uri, rust::Str name, rust::Str provider) noexcept {
    try {
        auto* layer = new ::QgsVectorLayer(
            from_rust(uri), from_rust(name), from_rust(provider));
        return ::std::make_unique<QgsVectorLayerHandle>(
            static_cast<void*>(layer));
    } catch (...) {
        return nullptr;
    }
}

bool vector_layer_is_valid(const QgsVectorLayerHandle& handle) noexcept {
    try {
        QGIS_NULL_GUARD(handle, false);
        return real_const(handle)->isValid();
    } catch (...) {
        return false;
    }
}

} // namespace qgis_shim::core
```

### Safety Rules

1. **Every function is `noexcept`** — exceptions must not cross the FFI boundary.
2. **Every function body is wrapped in `try/catch(...)`** — returns a safe default on error.
3. **Every function checks `QGIS_NULL_GUARD`** — handles null pointers gracefully.
4. **`void*` erases the real type** — the handle header never sees QGIS types.

## String Conversion (`convert.h`)

The `convert.h` header provides helpers for `QString` ↔ `rust::String`:

```cpp
inline rust::String to_rust(const QString& s) noexcept;
inline QString from_rust(rust::Str s) noexcept;
```

These use UTF-8 encoding via `QString::toUtf8()` / `QString::fromUtf8()`.

## Adding a New Type

Use the scaffold task:

```bash
pixi run scaffold core geometry QgsGeometry geometry
```

Then edit the generated files to add actual FFI functions. See [scaffold.md](/scaffold.md).
