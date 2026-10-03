---
id: TASK-43
title: Separate qgis-sdk hosted runtime from qgis-rs and qgis-py
status: To Do
assignee: []
created_date: '2026-10-03 09:35'
labels:
  - qgis-sdk
  - python
  - ffi
  - architecture
  - refactor
milestone: m-3
dependencies:
  - TASK-40
  - TASK-36
documentation:
  - >-
    backlog/docs/architecture/doc-7 -
    Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md
  - py-packages/qgis-sdk/pyproject.toml
  - crates/qgis-sdk/Cargo.toml
  - .knowledge/qgis-plugin-sdk.md
  - .agents/skills/refactor/SKILL.md
  - .agents/skills/tdd/SKILL.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make the QGIS plugin SDK dependency boundary explicit: qgis_sdk runtime uses PyQGIS/PyQt and QGIS lifecycle, qgis_sdk._core is optional tooling/acceleration, and qgis-sdk never directly depends on qgis-py. Provide an optional acceleration adapter only where the QGIS Python ABI is validated.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The qgis-sdk Rust and Python package dependency graph has no direct qgis-py dependency
- [ ] #2 Hosted UI, Processing, plugin lifecycle, task, feedback, and QGIS object ownership remain in qgis_sdk/PyQGIS/PyQt
- [ ] #3 Standalone qgis_rs remains independently installable and is not required by the base qgis-sdk package
- [ ] #4 Optional Rust acceleration has an explicit capability check, ABI/documentation policy, and tests for unavailable acceleration
- [ ] #5 No live QGIS or Qt objects cross qgis_rs._core, qgis_sdk._core, or Node NAPI boundaries
- [ ] #6 Compatibility imports, plugin lifecycle behavior, and QGIS-hosted tests remain green under offscreen serialized execution
<!-- AC:END -->
