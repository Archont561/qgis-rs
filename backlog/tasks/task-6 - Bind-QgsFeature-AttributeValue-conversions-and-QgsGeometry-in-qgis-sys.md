---
id: TASK-6
title: 'Bind QgsFeature, AttributeValue conversions, and QgsGeometry in qgis-sys'
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
labels:
  - qgis-sys
  - core
  - geometry
  - features
dependencies:
  - TASK-5
documentation:
  - .knowledge/decisions/D04-api-priority.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bind QgsFeature and QgsGeometry in qgis-sys, including extraction of attribute values (handling QVariant types into a safe Rust enum) and geometry export/import via WKB/WKT.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 C++ shim extracts attributes into structured primitive / string representations
- [ ] #2 Rust bridge exposes AttributeValue enum (Null, Bool, Int, Double, String, DateTime, Geometry)
- [ ] #3 QgsGeometry handle supports WKB bytes export (asWkb), WKT string export (asWkt), and construction from WKB/WKT
- [ ] #4 Tests verify attribute extraction and geometry WKB/WKT round-trip
<!-- AC:END -->
