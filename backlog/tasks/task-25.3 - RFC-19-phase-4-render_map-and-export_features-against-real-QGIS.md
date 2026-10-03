---
id: TASK-25.3
title: 'RFC 19 phase 4: render_map and export_features against real QGIS'
status: In Progress
assignee: []
created_date: '2026-10-02 23:23'
updated_date: '2026-10-03 19:21'
labels:
  - rfc
  - ffi
  - cpp
milestone: m-2
dependencies:
  - TASK-25.2
references:
  - 'https://github.com/Archont561/qgis-rs/issues/19'
documentation:
  - .knowledge/api-design.md
  - .knowledge/architecture.md
  - .knowledge/qgis-vector-layer.md
  - .knowledge/decisions/D09-wire-protocol-over-ffi.md
  - .knowledge/decisions/D12-qgis-native-manager-over-c-abi.md
  - .knowledge/decisions/INDEX.md
parent_task_id: TASK-25
priority: medium
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Phase 4 of RFC 19, the one that removes the placeholders.

Scope: render_map and export_features answer from real QGIS instead of the unimplemented envelope; the old static backend marker disappears from the Rust, Python and TypeScript suites and from the docs; capabilities stops being a static list and reports what the loaded backend can actually do, so a build without QGIS and a build with it answer differently and honestly.

This is also where the binary-artifact question gets settled in practice: a rendered map is bytes, and the current policy is that the wire carries a path rather than base64. Confirm or change that policy here, and write it down, because once a client depends on it the choice is hard to reverse.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 render_map and export_features answer from QGIS instead of the unimplemented envelope
- [ ] #2 The old static backend marker is gone from every suite and from the documentation
- [ ] #3 capabilities is computed from the loaded backend, so a build without QGIS and a build with it report different and accurate capability sets
- [ ] #4 The binary-artifact policy, a path on the wire rather than inline bytes, is confirmed or changed and written into the protocol documentation
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented native-manager render_map/export_features dispatch, path-based artifact responses, runtime capability reporting, optional QGIS/no-QGIS feature paths, and removed the stale static capability marker from suites and docs. The dispatch catalogue is now a handler registry, and a QGIS-backed integration fixture covers successful PNG rendering and GeoJSON export. Static Python/Node checks and git diff --check pass. Repository gates are still blocked in this checkout because pixi and cargo are not installed; do not treat the gates as green until run in the Pixi environment.
<!-- SECTION:NOTES:END -->
