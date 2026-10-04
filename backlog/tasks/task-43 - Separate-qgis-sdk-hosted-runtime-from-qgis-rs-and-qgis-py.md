---
id: TASK-43
title: Separate qgis-sdk hosted runtime from qgis-rs and qgis-py
status: To Do
assignee: []
created_date: '2026-10-03 09:35'
updated_date: '2026-10-04 12:48'
labels:
  - qgis-sdk
  - python
  - ffi
  - architecture
  - refactor
milestone: m-3
dependencies:
  - TASK-40
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

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-10-04 12:48
---
2026-10-04: dropped the TASK-36 dependency. TASK-43 is a dependency-boundary task under D13 - qgis_sdk never depends on qgis-py, and qgis_sdk._core stays optional tooling - while TASK-36 defines the declarative UI contract. The two are orthogonal: nothing in TASK-43 reads or changes the UI surface. The edge was blocking TASK-43, and TASK-44 behind it, on a task neither needs. TASK-40, which defines the product boundaries this task enforces, remains the real prerequisite and is Done.
---
<!-- COMMENTS:END -->
