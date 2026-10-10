---
id: TASK-41
title: Build the pure-Rust qgis-cli capability surface
status: In Progress
assignee: []
created_date: '2026-10-03 09:35'
updated_date: '2026-10-10 11:30'
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
- [x] #1 version, capabilities, and doctor report engine, transport, backend, limits, and unavailable native capabilities
- [ ] #2 validate, inspect, tiles plan, and batch plan expose deterministic machine-readable behavior with stable exit codes
- [ ] #3 Pure CLI tests run without QGIS, Python, Node, or WebEngine and preserve existing qgis-cli behavior
- [ ] #4 Native-only render/export/serve paths fail explicitly when the backend is unavailable and never silently substitute semantics
- [ ] #5 Filesystem policy, atomic artifacts, JSON stdout, stderr diagnostics, cancellation, and resource limits have contract tests
- [ ] #6 Implementation follows red-green-refactor slices and preserves existing public command flags and golden values
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The qgis-cli binary this task builds is what TASK-58 ships through @archont561/qgis-node and qgis-py.

Approved discovery slice: version, capabilities and doctor; binary and engine discovery public seams. Pure doctor exits 0 with optional native backend explicitly unavailable. Preserve existing commands; remaining TASK-41 slices stay open.

Discovery slice implemented: version/capabilities/doctor share deterministic text/JSON reports; engine owns availability, protocol owns names, clap owns command names. Existing engine_info wire response, flags, and execution gates are unchanged. Pure doctor exits 0 for optional QGIS absence. Red tests observed for missing engine seam and each new command; focused pure suites pass, native discovery tests pass. cargo tree and ldd confirm the no-default-features binary has no QGIS/Qt/Python/Node/WebEngine dependency. AC2-AC6 remain open for later slices; full gate evidence follows.

Final discovery-slice evidence: pixi run gates exit 0 (8/8); CARGO_NET_OFFLINE=true pixi run -- bun x turbo run test --env-mode=loose exit 0 (12/12). Rust 327 + 30 (was 323 + 30); SDK 490 passed/3 skipped/8 deselected, qt 3, qgis 5, qgis-py-dist 18, Bun 160, CTest 1 target. Separate native-feature discovery run: CLI 3 and engine 2 passed. Pure focused suites: 58 integration tests plus 1 doc test; clippy -D warnings passed. No push/PR; AC2-AC6 remain open.
<!-- SECTION:NOTES:END -->
