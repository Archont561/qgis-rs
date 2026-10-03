---
id: TASK-10
title: Bind QgsProject with ownership transfer semantics and QgsFeatureRequest
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
updated_date: '2026-10-03 08:31'
labels:
  - qgis-sys
  - qgis
  - project
  - editing
milestone: m-2
dependencies:
  - TASK-8
documentation:
  - backlog/docs/roadmap/doc-2 - QGIS-RS-Execution-Roadmap.md
  - .knowledge/qgis-vector-layer.md
  - .knowledge/decisions/D02-ownership-model.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement QgsProject CXX bindings and safe Rust Project wrapper adhering to D02 transfer semantics (add_layer consumes ownership), alongside QgsFeatureRequest builder filtering.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 QgsProject handle supports read(filename), write(), and addMapLayer(layer)
- [ ] #2 Safe Project::add_layer(self, layer: VectorLayer) consumes the VectorLayer handle to prevent double-free
- [ ] #3 Project::layer(&self, name_or_id) returns a borrowed layer reference
- [ ] #4 FeatureRequest builder supports bounding box rect and attribute expression filters
<!-- AC:END -->
