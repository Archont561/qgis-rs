---
type: Concept
title: QGIS Vector Layer
description: "QgsVectorLayer binding — creation, validity, metadata accessors."
status: stable
tags: [qgis, vector-layer, geo, features]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
sources:
  - id: qgis-vectorlayer-api
    resource: https://api.qgis.org/api/classQgsVectorLayer.html
    title: "QgsVectorLayer Class Reference — QGIS API Documentation"

---

# QGIS Vector Layer

## Overview

`QgsVectorLayer` is one of the most-used QGIS classes. It represents a layer of vector (feature) data — points, lines, or polygons — loaded from a data source via a provider plugin.

## Current Bindings

| FFI Function                     | Returns  | Purpose                            |
|----------------------------------|----------|------------------------------------|
| `vector_layer_new(uri, name, provider)` | `UniquePtr<QgsVectorLayerHandle>` | Create a new layer |
| `vector_layer_is_valid(handle)`  | `bool`   | Check if the layer loaded OK       |
| `vector_layer_name(handle)`      | `String` | Layer display name                 |
| `vector_layer_feature_count(handle)` | `i64` | Number of features (-1 on error) |
| `vector_layer_crs_authid(handle)` | `String` | CRS authority ID (e.g. `EPSG:4326`) |
| `vector_layer_geometry_type_name(handle)` | `String` | Geometry type (e.g. `Point`) |

## Provider Model

QGIS uses a plugin-based provider architecture. Common providers:

| Provider   | Data Source                              |
|------------|------------------------------------------|
| `ogr`      | OGR-supported formats (GeoPackage, Shapefile, GeoJSON, etc.) |
| `postgres` | PostgreSQL/PostGIS databases             |
| `wfs`      | OGC Web Feature Service                  |
| `memory`   | In-memory feature store                  |

The `vector_layer_new` constructor takes a URI string that the provider interprets. For `ogr`, this is typically a file path:

```rust
let layer = layer_ffi::vector_layer_new(
    "/path/to/data.gpkg", "my layer", "ogr"
);
```

## Test Fixture

The project includes `tests/fixtures/points.gpkg` — a GeoPackage with 3 point features in EPSG:4326. Tests use this to validate the binding:

```rust
#[test]
fn layer_feature_count() {
    let _app = helpers::AppHandle::new();
    let layer = open_test_layer();
    assert_eq!(layer_ffi::vector_layer_feature_count(&layer), 3);
}
```

## Future Additions

These are executable work items, not a second status tracker:

- Field/attribute schema access (`QgsFields`, `QgsField`) — [TASK-5](../backlog/tasks/task-5%20-%20Bind-QgsFields-and-QgsField-schema-types-in-qgis-sys.md)
- Feature and geometry values (`QgsFeature`, `QgsGeometry`) — [TASK-6](../backlog/tasks/task-6%20-%20Bind-QgsFeature-AttributeValue-conversions-and-QgsGeometry-in-qgis-sys.md)
- Feature iteration and CRS (`QgsFeatureIterator`, `QgsCoordinateReferenceSystem`) — [TASK-7](../backlog/tasks/task-7%20-%20Bind-QgsFeatureIterator-and-QgsCoordinateReferenceSystem-in-qgis-sys.md)
- Editing operations (`startEditing`, `addFeature`, `commitChanges`) — [TASK-11](../backlog/tasks/task-11%20-%20Bind-QgsVectorLayerEditBuffer-for-transactional-layer-editing.md)
- Batched manager-side feature access — [TASK-25.2](../backlog/tasks/task-25.2%20-%20RFC-19-phase-3-layer-open-info-close-and-a-batched-layer.features.md)
- Spatial filters, expressions, renderer and symbology — [TASK-9](../backlog/tasks/task-9%20-%20Implement-structured-error-handling-and-string-caching-across-Rust-wrappers.md), [TASK-14](../backlog/tasks/task-14%20-%20Implement-declarative-expression-engine-wrappers.md), and [TASK-12](../backlog/tasks/task-12%20-%20Bind-QgsMapSettings-and-QgsMapRendererSequentialJob-for-embedded-rendering.md)

The knowledge entry remains the binding reference; status, acceptance criteria, and dependency order live in Backlog.md.
