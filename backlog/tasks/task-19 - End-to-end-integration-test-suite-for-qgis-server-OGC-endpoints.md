---
id: TASK-19
title: End-to-end integration test suite for qgis-server OGC endpoints
status: To Do
assignee: []
created_date: '2026-09-30 20:49'
labels:
  - qgis-server
  - testing
  - ogc
dependencies: []
documentation:
  - .knowledge/api-design.md
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create an end-to-end integration test suite for qgis-server exercising WMS (GetCapabilities, GetMap), WFS (GetFeature), and OGC API Features against real .qgs/.qgz projects.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Test harness boots qgis-server on dynamic port or in-memory router
- [ ] #2 Tests assert WMS PNG output, WFS GeoJSON features, and XYZ tile slicing
- [ ] #3 Validated against test fixture project files
- [ ] #4 CI executes server integration tests in headless mode
<!-- AC:END -->
