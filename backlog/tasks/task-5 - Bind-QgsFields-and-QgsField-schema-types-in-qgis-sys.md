---
id: TASK-5
title: Bind QgsFields and QgsField schema types in qgis-sys
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
labels:
  - qgis-sys
  - core
  - schema
dependencies: []
documentation:
  - .knowledge/ROADMAP.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bind QgsFields and QgsField in qgis-sys with CXX handles to inspect layer attributes, types, and schema metadata according to Phase 1 data access roadmap and Decision D04.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 include/core/fields.h and src/core/fields/fields.rs declared with CXX bridge
- [ ] #2 C++ shim exposes field count, field name by index, field type, and precision
- [ ] #3 QgsFields handle accessor vector_layer_fields added to vector_layer FFI
- [ ] #4 Unit and integration test verifies field enumeration and metadata on test data
<!-- AC:END -->
