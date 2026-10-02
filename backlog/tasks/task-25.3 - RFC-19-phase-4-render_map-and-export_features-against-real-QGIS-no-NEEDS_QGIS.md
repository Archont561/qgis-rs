---
id: TASK-25.3
title: >-
  RFC 19 phase 4: render_map and export_features against real QGIS, no
  NEEDS_QGIS
status: To Do
assignee: []
created_date: '2026-10-02 23:23'
labels:
  - rfc
  - ffi
  - cpp
dependencies: []
references:
  - 'https://github.com/Archont561/qgis-rs/issues/19'
parent_task_id: TASK-25
priority: medium
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Phase 4 of RFC 19, the one that removes the placeholders.

Scope: render_map and export_features answer from real QGIS instead of the unimplemented envelope; the NEEDS_QGIS marker disappears from the Rust, Python and TypeScript suites and from the docs; capabilities stops being a static list and reports what the loaded backend can actually do, so a build without QGIS and a build with it answer differently and honestly.

This is also where the binary-artifact question gets settled in practice: a rendered map is bytes, and the current policy is that the wire carries a path rather than base64. Confirm or change that policy here, and write it down, because once a client depends on it the choice is hard to reverse.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 render_map and export_features answer from QGIS instead of the unimplemented envelope
- [ ] #2 The NEEDS_QGIS marker is gone from every suite and from the documentation
- [ ] #3 capabilities is computed from the loaded backend, so a build without QGIS and a build with it report different and accurate capability sets
- [ ] #4 The binary-artifact policy, a path on the wire rather than inline bytes, is confirmed or changed and written into the protocol documentation
<!-- AC:END -->
