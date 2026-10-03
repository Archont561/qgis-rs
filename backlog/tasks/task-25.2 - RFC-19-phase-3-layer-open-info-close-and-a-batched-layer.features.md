---
id: TASK-25.2
title: 'RFC 19 phase 3: layer open, info, close and a batched layer.features'
status: Done
assignee: []
created_date: '2026-10-02 23:23'
updated_date: '2026-10-03 18:39'
labels:
  - rfc
  - ffi
  - cpp
milestone: m-2
dependencies:
  - TASK-25.1
references:
  - 'https://github.com/Archont561/qgis-rs/issues/19'
documentation:
  - .knowledge/architecture.md
  - .knowledge/qgis-vector-layer.md
  - .knowledge/decisions/D09-wire-protocol-over-ffi.md
  - .knowledge/decisions/D12-qgis-native-manager-over-c-abi.md
  - .knowledge/decisions/INDEX.md
  - >-
    backlog/docs/architecture/doc-4 -
    QGIS-Native-Manager-and-API-Coverage-Strategy.md
parent_task_id: TASK-25
priority: medium
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Phase 3 of RFC 19. With the manager in place, add the layer lifecycle the registry was built for and the batched accessor ADR D06 asks for.

Scope: layer.open returning a registry id, layer.info returning the metadata the current shims expose one call at a time, layer.close releasing the entry, and a new layer.features that returns a page of features in one crossing instead of one call per feature. The batching is the point: the registry makes per-feature round trips possible, and ADR D06 says they are not allowed to become the normal path.

Every operation added here is an operation on the wire, so it needs the same treatment as the thirteen that exist: a closed enum arm, a request and response type in qgis-protocol, golden values that the Rust, Python and TypeScript suites all assert, and an error envelope for the layer-not-found and layer-already-closed cases rather than a crash or a null.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 layer.open, layer.info and layer.close are live operations backed by the registry, and closing twice answers with an error envelope rather than crashing
- [x] #2 layer.features returns a page of features in one crossing, and the per-feature round trip is not reintroduced anywhere
- [x] #3 The new operations have protocol types, closed enum arms and golden values asserted from Rust, Python and TypeScript alike
- [x] #4 A layer left open at shutdown is released by the manager, proven by a test
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented RFC 19 phase 3 through the dedicated native QGIS manager. Added layer_open, layer_info, layer_close, bounded layer_features pages, explicit owner-thread app_shutdown release accounting, protocol types, shared lifecycle fixtures, and Rust/Python/TypeScript golden coverage. Retired the superseded qgis-sys CXX/per-class shim tree and marked its backlog tasks deprecated.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
RFC 19 phase 3 is complete: layer lifecycle and batched feature access are registry-backed, bounded, copied over one manager crossing, and covered by cross-language protocol fixtures. Closed-layer errors and owner-thread shutdown release are tested.
<!-- SECTION:FINAL_SUMMARY:END -->
