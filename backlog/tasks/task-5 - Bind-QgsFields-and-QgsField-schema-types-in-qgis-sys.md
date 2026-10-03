---
id: TASK-5
title: Bind QgsFields and QgsField schema types in qgis-sys
status: Done
assignee: []
created_date: '2026-09-30 20:48'
updated_date: '2026-10-03 17:34'
labels:
  - qgis-sys
  - core
  - schema
milestone: m-1
dependencies: []
documentation:
  - backlog/docs/roadmap/doc-2 - QGIS-RS-Execution-Roadmap.md
  - .knowledge/qgis-vector-layer.md
  - .knowledge/scaffold.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bind QgsFields and QgsField in qgis-sys with CXX handles to inspect layer attributes, types, and schema metadata according to Phase 1 data access roadmap and Decision D04.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 include/core/fields.h and src/core/fields/fields.rs declared with CXX bridge
- [x] #2 C++ shim exposes field count, field name by index, field type, and precision
- [x] #3 QgsFields handle accessor vector_layer_fields added to vector_layer FFI
- [x] #4 Unit and integration test verifies field enumeration and metadata on test data
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03: Added the CXX fields bridge at crates/qgis-sys/include/core/fields.h and crates/qgis-sys/src/core/fields/fields.rs, with an opaque QgsFieldsHandle and count/name/type/precision accessors.

2026-10-03: Added the QgsFields C++ shim and vector_layer_fields accessor. vector_layer_fields owns a copy of QgsVectorLayer::fields(), while invalid field indices return empty strings or -1 without crossing Qt/QGIS types into Rust.

2026-10-03: Added layer_fields_expose_schema_metadata to crates/qgis-sys/tests/vector_layer.rs. pixi run -e default cargo test -p qgis-sys --no-default-features -- --test-threads=1 passed 6 vector-layer tests, including fid/Integer64 and name/String metadata.

2026-10-03: Updated .knowledge/qgis-vector-layer.md with the new field schema surface and ownership behavior.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
QgsFields and QgsField schema metadata are now available through an opaque CXX handle. Vector layers return an owned schema copy, Rust can enumerate field count/name/provider type/precision, invalid indices are guarded, and the QGIS integration test covers the fixture schema.
<!-- SECTION:FINAL_SUMMARY:END -->
