---
id: TASK-25.3
title: 'RFC 19 phase 4: render_map and export_features against real QGIS'
status: Done
assignee: []
created_date: '2026-10-02 23:23'
updated_date: '2026-10-03 22:11'
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
- [x] #1 render_map and export_features answer from QGIS instead of the unimplemented envelope
- [x] #2 The old static backend marker is gone from every suite and from the documentation
- [x] #3 capabilities is computed from the loaded backend, so a build without QGIS and a build with it report different and accurate capability sets
- [x] #4 The binary-artifact policy, a path on the wire rather than inline bytes, is confirmed or changed and written into the protocol documentation
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented native-manager render_map/export_features dispatch, path-based artifact responses, runtime capability reporting, optional QGIS/no-QGIS feature paths, and removed the stale static capability marker from suites and docs. The dispatch catalogue is now a handler registry, and a QGIS-backed integration fixture covers successful PNG rendering and GeoJSON export. Static Python/Node checks and git diff --check pass. Repository gates are still blocked in this checkout because pixi and cargo are not installed; do not treat the gates as green until run in the Pixi environment.

2026-10-04: proven, not just implemented. The restored pixi sandbox has QGIS, so the suite written for this task finally ran: `cargo test -p qgis-sys -p qgis-mcp --features qgis-sys/qgis,qgis-mcp/qgis -- --test-threads=1` — 9 + 1 qgis-sys tests and 11 qgis-mcp tests green, including `phase_four_operations_render_and_export_real_qgis_artifacts` (a 64x48 PNG written by QgsMapRendererSequentialJob, a 3-feature GeoJSON read back and parsed) and `phase_four_operations_are_native_and_return_path_errors_not_placeholders` (a missing project answers kind=qgis, never kind=unimplemented).

Why it had never run: `crates/package.json`'s test verb was `cargo test --workspace --no-default-features`, and these suites are `#![cfg(feature = "qgis")]`, so the gate compiled them out and printed "running 0 tests". That verb now chains a second run with the qgis features of qgis-sys and qgis-mcp, so AC#1 and AC#3 are regression-guarded instead of demonstrated once. AC#3 needs both halves and now has them: the QGIS-free run proves capabilities reports backend=unavailable with render_map/export_features unavailable, the QGIS run proves a loaded backend with both available and a qgis_version; capabilities_reports_the_loaded_backend asserts against cfg!(feature = "qgis") in both directions.

AC#2 verified by grep over the tree rather than by diff (this checkout is shallow, 2 commits): no static backend marker survives under crates/, py-packages/, ts-packages/, docs/ or .knowledge/, and no unimplemented envelope remains for either operation. AC#4: the path-based policy was recorded in D12 section 3; it is now also in the normative place, the crate-level documentation of qgis-protocol, which states what the response carries, who owns the written file, what overwrite does and does not promise, and that changing it means a new transport version.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
RFC 19 phase 4 closed on evidence rather than on implementation. render_map and export_features answer from real QGIS (PNG and GeoJSON artifacts asserted on disk), capabilities is computed from the loaded backend and now proves both of its answers, the static backend marker is gone from every suite and document, and the path-on-the-wire artifact policy is written into the qgis-protocol crate documentation as well as D12 section 3. The gate no longer compiles the proof away: crates/package.json runs the QGIS-feature suites of qgis-sys and qgis-mcp after the QGIS-free workspace run.
<!-- SECTION:FINAL_SUMMARY:END -->
