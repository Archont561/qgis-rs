---
id: TASK-7
title: Bind QgsFeatureIterator and QgsCoordinateReferenceSystem in qgis-sys
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
labels:
  - qgis-sys
  - core
  - iteration
  - crs
dependencies:
  - TASK-6
documentation:
  - .knowledge/ROADMAP.md
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
