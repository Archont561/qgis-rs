---
id: TASK-41
title: Build the pure-Rust qgis-cli capability surface
status: To Do
assignee: []
created_date: '2026-10-03 09:35'
labels:
  - cli
  - rust
  - testing
  - enhancement
milestone: m-3
dependencies:
  - TASK-40
documentation:
  - >-
    backlog/docs/architecture/doc-7 -
    Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md
  - crates/qgis-cli
  - crates/qgis-engine
  - crates/qgis-render
  - .agents/skills/refactor/SKILL.md
  - .agents/skills/tdd/SKILL.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the standalone GIS CLI contract from doc-7 without adding a PyQGIS/PyQt dependency to the pure path. Start with version, capabilities, doctor, validation, project manifest inspection, tile planning, batch planning, structured errors, deterministic artifacts, and explicit native-backend gates.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 version, capabilities, and doctor report engine, transport, backend, limits, and unavailable native capabilities
- [ ] #2 validate, inspect, tiles plan, and batch plan expose deterministic machine-readable behavior with stable exit codes
- [ ] #3 Pure CLI tests run without QGIS, Python, Node, or WebEngine and preserve existing qgis-cli behavior
- [ ] #4 Native-only render/export/serve paths fail explicitly when the backend is unavailable and never silently substitute semantics
- [ ] #5 Filesystem policy, atomic artifacts, JSON stdout, stderr diagnostics, cancellation, and resource limits have contract tests
- [ ] #6 Implementation follows red-green-refactor slices and preserves existing public command flags and golden values
<!-- AC:END -->
