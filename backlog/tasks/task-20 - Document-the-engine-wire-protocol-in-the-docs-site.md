---
id: TASK-20
title: Document the engine wire protocol in the docs site
status: To Do
assignee: []
created_date: '2026-10-02 22:35'
labels: []
dependencies: []
documentation:
  - .knowledge/decisions/D09-wire-protocol-over-ffi.md
priority: medium
type: docs
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The repository now speaks one versioned JSON protocol across every FFI boundary (D09), but the docs site still describes the per-language APIs only. Publish a reference page for the protocol itself: the request/response envelope, `transport_version` and what a mismatch does, the full operation table with payload and result shapes, and the `ErrorKind` list with how each client maps it to a native exception.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A reference page documents EngineRequest/EngineResponse and TRANSPORT_VERSION
- [ ] #2 Every Operation variant is listed with its payload and result shape
- [ ] #3 The ErrorKind table shows the Python exception and the JS EngineError kind for each
- [ ] #4 The page states the snake_case-on-the-wire rule and where the JS client renames
<!-- AC:END -->
