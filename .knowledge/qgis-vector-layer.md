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

Potential next bindings:
- Feature iteration (`QgsFeatureIterator`)
- Field/attribute access (`QgsFields`, `QgsField`)
- Geometry access (`QgsGeometry`, `QgsAbstractGeometry`)
- Editing operations (`startEditing`, `addFeature`, `commitChanges`)
- Spatial filters and expression filters
- Renderer and symbology access
