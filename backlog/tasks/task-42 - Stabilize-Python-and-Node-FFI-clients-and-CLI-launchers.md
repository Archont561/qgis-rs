---
id: TASK-42
title: Stabilize Python and Node FFI clients and CLI launchers
status: To Do
assignee: []
created_date: '2026-10-03 09:35'
labels:
  - ffi
  - python
  - node
  - typescript
  - cli
  - testing
milestone: m-3
dependencies:
  - TASK-40
  - TASK-31
documentation:
  - >-
    backlog/docs/architecture/doc-7 -
    Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md
  - crates/qgis-py/ARCHITECTURE.md
  - .knowledge/decisions/D09-wire-protocol-over-ffi.md
  - >-
    backlog/docs/testing/doc-5 -
    QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md
  - .agents/skills/tdd/SKILL.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Keep qgis-py and qgis-node thin protocol adapters while adding the shared capability, error, paging, artifact, cancellation, and launcher contract. Host-language wrappers provide ergonomic types; native addons do not mirror QGIS classes or expose CLI argv semantics.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each native addon exposes invoke(request_json) and transport_version as its stable native surface
- [ ] #2 Python and TypeScript clients consume shared protocol fixtures for capabilities, errors, pages, artifacts, and transport mismatch
- [ ] #3 Python and Node typed wrappers map structured errors without matching English error text and provide raw invoke escape hatches
- [ ] #4 Large results use pages/cursors or artifact metadata, and no raw QGIS/Qt pointer or QVariant crosses the boundary
- [ ] #5 Python and npm CLI launchers execute the canonical Rust binary without duplicate command semantics or silent fallbacks
- [ ] #6 FFI, launcher, and cross-language tests run through the existing Qt/QGIS/WebEngine gates without requiring WebEngine for pure operations
<!-- AC:END -->
