---
type: Decision
id: D04
title: "API Binding Priority — What to Bind and When"
description: "Tiered approach to binding QGIS types — the 20% that covers 80% of real workflows, in dependency order."
status: draft
tags: [roadmap, api, priority]
date: 2026-09-17T00:00:00Z
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# D04: API Binding Priority

## Principle

Don't try to bind all 1,500 QGIS classes. Bind the **20% that covers 80% of real workflows**, in dependency order. Each tier unlocks the next.

## Tier 0 — Foundation (current)

Already bound. No further work needed at the FFI level.

| Type | Status |
|------|--------|
| `QgsApplication` | ✅ bound, workaround documented |
| `QgsVectorLayer` (basic metadata) | ✅ bound |

## Tier 1 — Data Access (next)

Unlocks: reading features, inspecting schemas, basic spatial queries.

| Type | Why | Shim Complexity |
|------|-----|-----------------|
| `QgsFields` + `QgsField` | Layer schema — needed to interpret features | Medium (implicitly shared) |
| `QgsFeatureIterator` | Read features from a layer | High (iterator protocol) |
| `QgsFeature` | One row of data | High (attributes as QVariant) |
| `QgsGeometry` | Spatial operations | Very High (WKB/WKT, many methods) |
| `QgsCoordinateReferenceSystem` | CRS lookups | Medium (implicitly shared) |

**Key challenge**: `QgsFeature::attributes()` returns `QList<QVariant>`. The QVariant type erasure needs a Rust-side enum:

```rust
pub enum AttributeValue {
    Null,
    Bool(bool),
    Int(i64),
    Double(f64),
    String(String),
    DateTime(String),  // ISO-8601
    Geometry(Geometry),
    // ...
}
```

This requires a bridge function that inspects each QVariant's type and extracts the value — about 10 FFI functions for the common types.

## Tier 2 — Project & Editing (after Tier 1)

Unlocks: multi-layer projects, editing workflows, saving.

| Type | Why | Key Challenge |
|------|-----|---------------|
| `QgsProject` | Central state container | **Ownership transfer** (D02) |
| `QgsVectorLayerEditBuffer` | Editing transactions | RAII scope guard |
| `QgsVectorDataProvider` | Write features back | Provider abstraction |
| `QgsFeatureRequest` | Filtered iteration | Builder pattern |
| `QgsCoordinateTransform` | Reproject on the fly | Context-dependent |

**Key challenge**: `QgsProject::addMapLayer()` transfers ownership. This is where D02's ownership model gets its real test.

## Tier 3 — Rendering & Output (later)

Unlocks: map images, PDF export, styling.

| Type | Why | Key Challenge |
|------|-----|---------------|
| `QgsMapSettings` | Configure a render | Many properties |
| `QgsMapRendererJob` | Async rendering | Signals / threading |
| `QgsSymbol` | Styling | Deep class hierarchy |
| `QgsLayout` | Print layouts | Complex object graph |

**This is where signals become necessary** — `QgsMapRendererJob::renderingFinished()` is a signal. This is the trigger point for considering cxx-qt.

## What NOT to Bind

| Area | Why Not |
|------|---------|
| `QgsMapCanvas` (QWidget) | GUI widget — Rust users want headless |
| Plugin API | QGIS plugins are Python/C++; Rust plugins would need a different model |
| Processing framework | Wraps GDAL/GRASS/SAGA — call those directly |
| 3D / `Qgs3DMapScene` | Niche, depends on Qt3D |
| Server / `QgsServer` | Different deployment model |

## Suggested Order

```
Now:    D01 (two-crate arch) + D02 (ownership) + D03 (errors)
        ↓
Next:   Tier 1 — QgsFields, QgsFeatureIterator, QgsFeature, QgsGeometry
        ↓
Then:   Tier 2 — QgsProject (tests the ownership model)
        ↓
Later:  Tier 3 — Rendering (triggers cxx-qt evaluation)
```
