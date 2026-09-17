---
type: Reference
title: Related Approaches
description: Comparison of Rust ↔ C++ / Qt binding strategies and how qgis-rs relates to them.
status: stable
tags: [cxx, cxx-qt, autocxx, bindgen, qt-bridges, comparison]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
sources:
  - id: cxx-repo
    resource: https://github.com/dtolnay/cxx
    title: "CXX — Safe interop between Rust and C++"
    author: human:dtolnay
  - id: cxx-qt-repo
    resource: https://github.com/KDAB/cxx-qt
    title: "CXX-Qt — Safe interop between Rust and Qt"
    author: team:kdab
  - id: autocxx-repo
    resource: https://github.com/google/autocxx
    title: "autocxx — automatically generate CXX bridge from C++ headers"
    author: team:google
  - id: qmetaobject-rs
    resource: https://github.com/woboq/qmetaobject-rs
    title: "qmetaobject — Rust crate for Qt QObject"
    author: team:woboq
  - id: oxigis
    resource: https://github.com/cool-japan/oxigis
    title: "OxiGIS — Pure Rust GIS application"

---

# Related Approaches

qgis-rs sits at the intersection of two binding challenges: **Rust ↔ C++** (QGIS is C++) and **Rust ↔ Qt** (QGIS depends on Qt). Several tools address these problems with different trade-offs.

## Rust ↔ C++ Interop

### cxx (used by qgis-rs)

**Repo:** [dtolnay/cxx](https://github.com/dtolnay/cxx) — 47M+ downloads on crates.io

The foundation of qgis-rs's FFI strategy. CXX provides:
- **Compile-time safety** — signatures in the `#[cxx::bridge]` are checked against C++ via static assertions
- **Zero-cost abstraction** — no serialization, no runtime checks, no copying
- **Native type support** — `String` ↔ `rust::String`, `Vec<T>` ↔ `rust::Vec<T>`, `UniquePtr<T>`, etc.
- **Code generation** — both Rust and C++ glue code generated from one source of truth

**Why qgis-rs uses cxx:** QGIS has a complex C++ API with templates, virtual methods, and Qt-specific patterns. CXX's opaque type model lets us wrap these without exposing their internals to Rust, while the type-checked bridge prevents ABI mismatches.

**Limitations:** CXX doesn't support:
- Inheritance / virtual dispatch from Rust
- Template instantiation in the bridge
- Qt's meta-object system (signals, slots, properties)
- Returning references with lifetimes tied to arguments

### autocxx

**Repo:** [google/autocxx](https://github.com/google/autocxx)

Automatically generates CXX bridges from C++ headers, reducing manual signature writing. Uses `bindgen` internally to parse headers, then emits `#[cxx::bridge]` modules.

**Pros:** Less boilerplate for large APIs.
**Cons:** Generated bridges can be unwieldy; doesn't handle all C++ patterns; less control over the API surface.

**Why not for qgis-rs:** QGIS headers pull in the entire Qt type system, and many QGIS methods use patterns autocxx can't represent (reference returns, implicit conversions, Qt macros). Manual shims give precise control.

### bindgen + cc

**Repo:** [rust-lang/rust-bindgen](https://github.com/rust-lang/rust-bindgen)

Generates raw `extern "C"` FFI bindings from C/C++ headers. The traditional approach.

**Pros:** Works with any C/C++ library; well-understood.
**Cons:** All calls are `unsafe`; no type-safe string/container interop; manual memory management; C++ name mangling is fragile.

**Why not for qgis-rs:** Raw bindgen output would expose the full complexity of QGIS's C++ ABI, including vtables and template instantiations. The shim pattern provides a cleaner, safer interface.

### cpp! (cpp crate)

**Repo:** [mystor/rust-cpp](https://github.com/mystor/rust-cpp)

Embeds C++ code directly inside Rust files via the `cpp!` macro.

**Pros:** Very low friction for small snippets.
**Cons:** No type checking across the boundary; hard to maintain for large APIs; no shared type definitions.

**Why not for qgis-rs:** The QGIS API is too large for inline C++ snippets. The three-file pattern (header / bridge / shim) provides better organization and compile-time verification.

## Rust ↔ Qt Interop

### cxx-qt (KDAB)

**Repo:** [KDAB/cxx-qt](https://github.com/KDAB/cxx-qt) — actively maintained

A superset of CXX that adds Qt-specific code generation for:
- Implementing `QObject` subclasses in Rust
- Qt signals and slots
- QML type registration
- Qt property system

Provides `cxx-qt-lib` with bindings to common QtCore/QtGui types (QString, QByteArray, QVariant, etc.).

**Relevance to qgis-rs:** cxx-qt is the most relevant adjacent project. If qgis-rs ever needs to:
- Expose Rust objects to QML
- Connect Rust functions to Qt signals
- Use Qt container types natively

...then cxx-qt's code generation would be valuable. Currently qgis-rs avoids Qt types at the bridge level, converting to/from Rust types in the shim layer.

### Qt Bridges (official Qt)

Qt's own [Qt Bridges](https://doc.qt.io/qt-6/qtbindingstointroduction.html) project (announced 2025) aims to provide official Rust support via a CXX-based approach. Focused on QML backends rather than full Qt API coverage.

**Status:** Early-stage. Not yet suitable for production QGIS integration.

### qmetaobject

**Repo:** [woboq/qmetaobject-rs](https://github.com/woboq/qmetaobject-rs)

Uses the `cpp!` macro plus Rust procedural macros to create QObject subclasses from Rust structs. Supports QML but not QWidgets.

**Status:** Maintained but limited scope.

## Other GIS Rust Bindings

| Project          | Target       | Approach                  | Status       |
|------------------|--------------|---------------------------|--------------|
| `gdal`           | GDAL C API   | bindgen + safe wrapper    | Active       |
| `geos`           | GEOS C API   | bindgen + safe wrapper    | Active       |
| `proj`           | PROJ C API   | bindgen + safe wrapper    | Active       |
| `qgis-rs`        | QGIS C++ API | cxx + manual shims        | Early stage  |
| `rust-qgis`      | QGIS C++ API | bindgen                   | Abandoned    |

Most geospatial Rust crates bind **C** APIs (GDAL, GEOS, PROJ), which are much simpler to wrap. QGIS is unique in exposing a rich **C++** API, requiring a more sophisticated approach.

## Why CXX + Manual Shims?

The qgis-rs architecture was chosen because:

1. **QGIS headers are too complex for automatic binding** — they pull in Qt, template-heavy STL, and QGIS-internal types
2. **The API surface is enormous** — manual shims let us bind incrementally, one type at a time
3. **Safety is paramount** — CXX's static checks catch mismatches that `bindgen` + manual `unsafe` would miss
4. **Qt avoidance at the bridge level** — by converting Qt types in the shim, the Rust API stays Qt-free
5. **Scaffoldable** — the three-file pattern is mechanical enough to template (see `pixi run scaffold`)

## Comparison Matrix

| Feature               | qgis-rs (cxx+shim) | autocxx | bindgen+cc | cxx-qt    |
|-----------------------|---------------------|---------|------------|-----------|
| Type safety           | ✅ compile-time      | ✅       | ❌ runtime  | ✅         |
| Qt signal/slot        | ❌                   | ❌       | ❌          | ✅         |
| QML integration       | ❌                   | ❌       | ❌          | ✅         |
| Incremental binding   | ✅ one type at a time| ⚠️ all-or-nothing | ⚠️  | ⚠️        |
| No Qt in Rust API     | ✅                   | ⚠️       | ⚠️          | ⚠️        |
| Exception safety      | ✅ try/catch in shim | ⚠️       | ❌          | ⚠️        |
| Opaque handle pattern | ✅                   | ⚠️       | ❌          | ✅        |
