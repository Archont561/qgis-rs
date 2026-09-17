---
type: Decision
id: D06
title: "String Strategy — Convert at the Boundary"
description: "Convert QString to Rust String at the FFI boundary, cache metadata with OnceCell, batch-extract for hot paths."
status: draft
tags: [strings, performance, qstring, conversion]
date: 2026-09-17T00:00:00Z
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# D06: String Strategy

## The Reality

Every string crossing the FFI boundary pays for a conversion:

```
Rust &str → QString::fromUtf8()   (allocate + UTF-8→UTF-16)
QString → .toUtf8() → rust::String (allocate + UTF-16→UTF-8)
```

For a layer with 100,000 features each having 5 string attributes, that's 500,000 double-conversions during iteration.

## Decision

### Short-term: accept the cost, measure before optimizing

The current `convert.h` approach is correct and safe. Premature optimization of string conversion is not worth the complexity until profiling proves it's a bottleneck.

### Medium-term: bulk extraction for hot paths

For feature iteration, add a **batch accessor** that extracts all string attributes in one FFI call:

```cpp
// Instead of N individual calls:
rust::Vec<rust::String> feature_all_string_attributes(
    const QgsFeatureHandle& feature) noexcept;
```

This amortizes the FFI overhead (function call + exception frame) even if each string still converts.

### Long-term: zero-copy where possible

For read-only access to layer metadata (name, CRS authid, etc.), the safe crate can cache values:

```rust
pub struct VectorLayer {
    inner: UniquePtr<QgsVectorLayerHandle>,
    cached_name: OnceCell<String>,    // lazily populated
    cached_crs: OnceCell<String>,
}

impl VectorLayer {
    pub fn name(&self) -> &str {
        self.cached_name.get_or_init(|| {
            ffi::vector_layer_name(&self.inner)
        })
    }
}
```

Layer metadata doesn't change after creation (usually), so caching is safe and eliminates repeat conversions.

## What NOT to Do

- **Don't** try to expose `QString` as an opaque type and defer conversion — it just pushes the cost to the user and makes the API awkward
- **Don't** use `CxxString` (std::string) instead of `rust::String` — QGIS doesn't use std::string, it uses QString
- **Don't** try to share QString's implicit sharing with Rust — the reference counting semantics don't translate
