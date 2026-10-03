---
id: TASK-38
title: 'Add typed QGIS fields, validation, and UI state binding'
status: To Do
assignee: []
created_date: '2026-10-03 09:19'
labels:
  - qgis-sdk
  - ui
  - forms
  - qgis
dependencies:
  - TASK-36
documentation:
  - >-
    backlog/docs/ui/doc-6 -
    QGIS-SDK-Native-UI-Kit-and-Visual-Design-Loop-Strategy.md
  - >-
    backlog/docs/testing/doc-5 -
    QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md
  - .knowledge/qgis-plugin-ui.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the typed form model behind the native UI kit. Add basic and QGIS-aware fields, structured validation, dirty/reset/apply behavior, asynchronous validation hooks, QSettings persistence, and adapters for native layer, field, CRS, extent, expression, feature-source, map-scale, and raster-band controls.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 FieldSpec and FieldState are separate from Qt widgets and can be tested in pure Python.
- [ ] #2 Basic fields provide typed values, required/minimum/maximum rules, and structured field/form validation errors.
- [ ] #3 QGIS-aware fields adapt native QGIS widgets rather than reimplementing their selection behavior.
- [ ] #4 Form values, dirty state, reset, apply-without-closing, and QSettings persistence have deterministic tests.
- [ ] #5 QGIS objects stay on the owning Qt/QGIS thread and missing QGIS widgets produce explicit capability errors.
- [ ] #6 Hypothesis strategies cover pure field specifications and validation values without generating live QGIS objects.
<!-- AC:END -->
