---
id: TASK-25.2
title: 'RFC 19 phase 3: layer open, info, close and a batched layer.features'
status: To Do
assignee: []
created_date: '2026-10-02 23:23'
updated_date: '2026-10-03 02:16'
labels:
  - rfc
  - ffi
  - cpp
dependencies:
  - TASK-25.1
references:
  - 'https://github.com/Archont561/qgis-rs/issues/19'
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
- [ ] #1 layer.open, layer.info and layer.close are live operations backed by the registry, and closing twice answers with an error envelope rather than crashing
- [ ] #2 layer.features returns a page of features in one crossing, and the per-feature round trip is not reintroduced anywhere
- [ ] #3 The new operations have protocol types, closed enum arms and golden values asserted from Rust, Python and TypeScript alike
- [ ] #4 A layer left open at shutdown is released by the manager, proven by a test
<!-- AC:END -->
