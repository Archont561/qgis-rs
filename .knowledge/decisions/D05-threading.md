---
type: Decision
id: D05
title: "Threading — Accept Single-Threaded, Design for the Future"
description: "Accept single-threaded execution — all QGIS types are !Send + !Sync, matching Qt thread affinity."
status: draft
tags: [threading, concurrency, qt, design]
date: 2026-09-17T00:00:00Z
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# D05: Threading Model

## Decision

**Accept single-threaded execution as the current reality.** Design the safe API so this constraint is explicit, not a surprise.

## Implementation

### All QGIS types are `!Send + !Sync`

```rust
pub struct VectorLayer {
    inner: cxx::UniquePtr<qgis_sys::vector_layer_ffi::QgsVectorLayerHandle>,
    // PhantomData makes this !Send + !Sync
    _not_send: PhantomData<*const ()>,
}
```

This means the Rust compiler **prevents** passing QGIS objects to other threads:

```rust
// This won't compile:
let layer = VectorLayer::open("data.gpkg", "pts", "ogr")?;
std::thread::spawn(move || {
    println!("{}", layer.name());  // error: VectorLayer is not Send
});
```

### The escape hatch: extract data, send the data

QGIS objects stay on the main thread. Extracted data (strings, numbers, geometries as WKB bytes) can be sent freely:

```rust
let layer = VectorLayer::open("data.gpkg", "pts", "ogr")?;
let names: Vec<String> = layer.features()
    .map(|f| f.attribute_string("name"))
    .collect();

// NOW send to another thread:
std::thread::spawn(move || {
    for name in &names {
        println!("{name}");  // fine — these are plain Strings
    }
});
```

### `!Send` is a feature, not a bug

This matches Qt's own threading model: QObjects have thread affinity. Trying to use them from another thread in C++ is undefined behavior. Rust's type system catches this at compile time instead of runtime.

## Future: If QGIS Adds Thread-Safe APIs

If QGIS introduces thread-safe APIs (e.g., for background rendering or parallel feature processing), specific types can be explicitly marked `Send`:

```rust
// Hypothetical future:
unsafe impl Send for RenderResult {}  // if QGIS guarantees it
```

This is a per-type opt-in, not a blanket change.
