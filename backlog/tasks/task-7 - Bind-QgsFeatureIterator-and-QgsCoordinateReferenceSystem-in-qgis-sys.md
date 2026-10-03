---
id: TASK-7
title: Bind QgsFeatureIterator and QgsCoordinateReferenceSystem in qgis-sys
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
updated_date: '2026-10-03 08:31'
labels:
  - qgis-sys
  - core
  - iteration
  - crs
milestone: m-1
dependencies:
  - TASK-6
documentation:
  - backlog/docs/roadmap/doc-2 - QGIS-RS-Execution-Roadmap.md
  - .knowledge/qgis-vector-layer.md
  - .knowledge/scaffold.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bind QgsFeatureIterator for streaming features from vector layers and QgsCoordinateReferenceSystem (Crs) for spatial reference lookups.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 C++ shim provides vector_layer_get_features returning QgsFeatureIteratorHandle
- [ ] #2 feature_iterator_next(handle, out_feature) supports cursor iteration over layer features
- [ ] #3 QgsCoordinateReferenceSystem handle exposes authid, srsid, description, and toWkt
- [ ] #4 Rust integration test demonstrates iterating all features in a vector layer and reading attributes
<!-- AC:END -->
