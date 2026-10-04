---
id: TASK-11
title: Bind QgsVectorLayerEditBuffer for transactional layer editing
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
updated_date: '2026-10-04 12:48'
labels:
  - qgis-sys
  - qgis
  - editing
  - deprecated
milestone: m-2
dependencies: []
documentation:
  - backlog/docs/roadmap/doc-2 - QGIS-RS-Execution-Roadmap.md
  - .knowledge/qgis-vector-layer.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bind vector layer editing buffers in qgis-sys and create safe EditSession RAII guards for inserting, updating, and deleting features with commit/rollback.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 C++ shims expose startEditing, addFeature, deleteFeature, changeAttributeValue, commitChanges, and rollBack
- [ ] #2 Safe EditSession RAII guard commits or rolls back edits on drop
- [ ] #3 Full round-trip test creates features, commits to disk, and verifies persistence
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
