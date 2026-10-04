---
id: TASK-10
title: Bind QgsProject with ownership transfer semantics and QgsFeatureRequest
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
updated_date: '2026-10-04 12:48'
labels:
  - qgis-sys
  - qgis
  - project
  - editing
  - deprecated
milestone: m-2
dependencies: []
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

## Comments

<!-- COMMENTS:BEGIN -->
author: Arena agent
created: 2026-10-03 18:36
---
Deprecated: superseded by RFC 19 native-manager operations; this legacy direct qgis-sys shim path is no longer planned.
---

created: 2026-10-04 12:48
---
2026-10-04: archived as superseded, not implemented. This task belongs to the per-concept cxx bridge that RFC 19 replaced with the native manager. D12 says it plainly: the qgis-sys CXX shims are useful implementation references but they are not the RFC 19 boundary. No cxx::bridge remains anywhere in the repository, and the functional equivalents already shipped behind qgis_invoke in TASK-25.2 for layer open, info, close and features, and TASK-25.3 for render_map and export_features. The task already carried the deprecated label; this move applies that ruling to its status and clears the dangling dependency edge it left behind. Reopen by un-archiving if a direct shim path is ever planned again.
---
<!-- COMMENTS:END -->
