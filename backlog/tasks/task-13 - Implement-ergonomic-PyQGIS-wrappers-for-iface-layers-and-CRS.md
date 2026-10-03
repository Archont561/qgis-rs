---
id: TASK-13
title: 'Implement ergonomic PyQGIS wrappers for iface, layers, and CRS'
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
updated_date: '2026-10-03 08:31'
labels:
  - qgis-sdk
  - python
  - api
milestone: m-3
dependencies: []
documentation:
  - .knowledge/qgis-plugin-sdk.md
  - .knowledge/qgis-plugin-ui.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build the Pythonic wrappers in qgis_sdk.qgis for active layer access, layer lookup, spatial reference helpers, and interface utilities without verbose C++ boilerplate.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 qgis_sdk.layers provides Pythonic layer querying, attribute dict conversion, and feature iteration
- [ ] #2 qgis_sdk.crs provides CRS transforms and coordinate conversions
- [ ] #3 Works in live QGIS runtime and with fake fallbacks in pure Python tests
<!-- AC:END -->
