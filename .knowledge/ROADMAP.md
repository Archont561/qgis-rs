---
type: Strategy
title: Roadmap
description: "Ordered plan for qgis-rs — architectural decisions first, then incremental type binding."
status: draft
tags: [roadmap, strategy, decisions]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# Roadmap

## Phase 0 — Architectural Foundation (now)

Before binding more types, establish the patterns that every future type will follow.

| Task | Decision | Status |
|------|----------|--------|
| Two-crate architecture | [D01](/decisions/D01-two-crate-architecture.md) | Proposed |
| Ownership model | [D02](/decisions/D02-ownership-model.md) | Proposed |
| Error handling | [D03](/decisions/D03-error-handling.md) | Proposed |
| Threading model | [D05](/decisions/D05-threading.md) | Proposed |
| String strategy | [D06](/decisions/D06-string-strategy.md) | Proposed |
| API priority | [D04](/decisions/D04-api-priority.md) | Proposed |

**Deliverable:** `crates/qgis/` skeleton with `Application` and `VectorLayer` safe wrappers that demonstrate the patterns.

## Phase 1 — Data Access

Bind the types needed to read features from a layer.

```
QgsFields → Fields
QgsField → Field
QgsFeatureIterator → impl Iterator<Item = Feature>
QgsFeature → Feature
QgsGeometry → Geometry (WKB/WKT round-trip)
QgsCoordinateReferenceSystem → Crs
```

**Validation scenario:**
```rust
let app = Application::new()?;
let layer = VectorLayer::open("points.gpkg", "pts", "ogr")?;
for feature in layer.features() {
    let name = feature.attribute_string("name");
    let geom = feature.geometry();
    println!("{name}: {}", geom.as_wkt()?);
}
```

## Phase 2 — Project & Editing

Tests the ownership model (D02) with real ownership transfers.

```
QgsProject → Project (add_layer consumes VectorLayer)
QgsFeatureRequest → FeatureRequest (builder pattern)
QgsVectorLayerEditBuffer → editing transaction RAII guard
```

**Validation scenario:**
```rust
let mut project = Project::new();
let layer = VectorLayer::open("out.gpkg", "new_pts", "ogr")?;
project.add_layer(layer);  // ownership transferred
let borrowed = project.layer("new_pts").unwrap();
let mut edit = borrowed.start_editing()?;
edit.add_feature(new_feature)?;
edit.commit()?;
```

## Phase 3 — Rendering (triggers cxx-qt evaluation)

Rendering needs signals (`renderingFinished()`). This is the decision point for adding cxx-qt as a dependency.

**Options:**
1. **cxx-qt**: full QObject support, signals/slots, but heavier build
2. **Polling**: spin the Qt event loop manually, check flags — simpler but ugly
3. **Callback bridge**: C++ QObject subclass forwards signals to Rust via function pointers — middle ground

## What We Deliberately Skip

- GUI widgets (`QgsMapCanvas`, `QgsLayerTreeView`) — headless-only
- Plugin API — Rust plugins would need a fundamentally different model
- Processing framework — call GDAL/GRASS crates directly
- 3D rendering — niche, Qt3D dependency

## Decision Log

| ID | Decision | Status |
|----|----------|--------|
| D01 | Two-crate architecture | Proposed |
| D02 | Ownership model (transfer semantics) | Proposed |
| D03 | Error handling (structured Results) | Proposed |
| D04 | API binding priority | Proposed |
| D05 | Threading (single-threaded, `!Send`) | Proposed |
| D06 | String strategy (convert at boundary) | Proposed |
