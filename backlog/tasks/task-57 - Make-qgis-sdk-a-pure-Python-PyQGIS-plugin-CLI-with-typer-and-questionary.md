---
id: TASK-57
title: Make qgis-sdk a pure-Python PyQGIS plugin CLI with typer and questionary
status: To Do
assignee: []
created_date: '2026-10-09 15:47'
labels:
  - qgis-sdk
dependencies: []
priority: high
type: enhancement
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 qgis-sdk is a pure-Python console script with no Rust, no _core and no pyo3 build
- [ ] #2 The CLI never imports PyQGIS or qgis_py, and the plugin zip contains no qgis_sdk code
- [ ] #3 questionary prompts cover the non-web scaffold choices, and every prompt has a flag for CI
- [ ] #4 qgis-sdk package builds the plugin zip, and the test suite runs without QGIS
<!-- AC:END -->
