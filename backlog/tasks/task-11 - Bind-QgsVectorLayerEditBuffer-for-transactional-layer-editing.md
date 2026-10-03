---
id: TASK-11
title: Bind QgsVectorLayerEditBuffer for transactional layer editing
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
updated_date: '2026-10-03 18:36'
labels:
  - qgis-sys
  - qgis
  - editing
  - deprecated
milestone: m-2
dependencies:
  - TASK-10
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
<!-- COMMENTS:END -->
