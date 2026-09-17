---
type: Decision
id: D02
title: "Ownership Model — Transfer Semantics"
description: "Transfer semantics for Qt parent-child ownership vs Rust ownership — owned, transferred, and borrowed handle types."
status: draft
tags: [ownership, memory, safety, qt]
date: 2026-09-17T00:00:00Z
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# D02: Ownership Model — Transfer Semantics

## The Problem

QGIS has three ownership patterns:

1. **Caller-owned**: `new QgsVectorLayer(...)` — you created it, you delete it
2. **Transferred**: `QgsProject::addMapLayer(layer)` — project takes ownership, deletes it when removed
3. **Borrowed**: `layer->fields()` — returns `const QgsFields&`, lifetime tied to the layer

Rust needs to know which pattern applies at compile time. Getting this wrong causes:
- **Double-free**: both Rust and QGIS try to delete the same object
- **Use-after-free**: Rust holds a handle to an object QGIS already deleted
- **Memory leak**: neither side deletes the object

## Decision

Use a **three-type ownership model** in the safe `qgis` crate:

### Owned Handles (caller-owned)

```rust
// qgis::VectorLayer — Rust owns this, drops it on scope exit
let layer = VectorLayer::new("points.gpkg", "points", "ogr")?;
assert!(layer.is_valid());
println!("{}", layer.name());  // safe — Rust owns it
// layer dropped here → C++ delete
```

The wrapper holds `UniquePtr<QgsVectorLayerHandle>` and calls the destructor on `Drop`.

### Transferred Handles (ownership moves to QGIS)

```rust
let layer = VectorLayer::new("points.gpkg", "points", "ogr")?;
let project = Project::new();

// add_layer() CONSUMES the layer — ownership transfers to QGIS
project.add_layer(layer);  // layer is moved, cannot be used after this

// To access it, get a borrowed reference back:
let borrowed = project.layer_by_name("points").unwrap();
println!("{}", borrowed.name());  // safe — project keeps it alive
```

After transfer, the Rust wrapper is consumed (`layer` is moved). The only way to access the object is through the project, which returns a **borrowed reference**.

### Borrowed References (non-owning)

```rust
// BorrowedRef<'project> — lifetime tied to the project
let layer: BorrowedLayer<'_> = project.layer_by_name("points").unwrap();
let fields: Fields = layer.fields();  // returns owned copy (CXX limitation)
let crs: Crs = layer.crs();          // returns owned copy
```

Borrowed references are `!Send`, `!Sync`, and carry a lifetime tied to their owner. They cannot outlive the parent object.

## Implementation

```rust
// In qgis crate:

pub struct VectorLayer {
    inner: cxx::UniquePtr<qgis_sys::vector_layer_ffi::QgsVectorLayerHandle>,
}

impl VectorLayer {
    pub fn new(uri: &str, name: &str, provider: &str) -> Result<Self> {
        let inner = qgis_sys::vector_layer_ffi::vector_layer_new(uri, name, provider);
        if inner.is_null() {
            return Err(QgisError::LayerCreationFailed { uri: uri.into() });
        }
        Ok(Self { inner })
    }
}

// When transferred to Project, the handle pointer is extracted and the
// Rust wrapper is consumed without calling Drop:
pub struct Project { /* ... */ }

impl Project {
    pub fn add_layer(&mut self, layer: VectorLayer) {
        // Extract the raw pointer, prevent Rust Drop from running
        let ptr = ManuallyDrop::new(layer.inner);
        // Transfer ownership to QGIS via a new FFI call
        qgis_sys::project_ffi::project_add_layer(self.inner.pin_mut(), ptr);
    }
}
```

## What This Means for qgis-sys

qgis-sys needs a new FFI function for ownership transfer:

```cpp
// In the shim:
void project_add_layer(ProjectHandle& project,
                       ::std::unique_ptr<QgsVectorLayerHandle> layer) noexcept;
```

The `unique_ptr` parameter transfers ownership from Rust to C++. After the call, QGIS owns the `QgsVectorLayer*` and will delete it when the project removes it.

## Open Questions

- How to handle `QgsProject::removeMapLayer()`? Does Rust get ownership back, or does QGIS delete the layer?
  - **Answer**: QGIS deletes it. Rust's `BorrowedLayer` becomes invalid. Use `QPointer`-style weak tracking.
- What about objects that can be either owned or borrowed depending on context (e.g., `QgsGeometry` returned from a feature vs. created standalone)?
  - **Answer**: Two types: `Geometry` (owned) and `GeometryRef<'feature>` (borrowed).
