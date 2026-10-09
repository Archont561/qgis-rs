---
id: TASK-60
title: 'Remove deprecated aliases, stale names and unpublished references'
status: In Progress
assignee: []
created_date: '2026-10-09 15:47'
updated_date: '2026-10-09 15:57'
labels:
  - cleanup
dependencies: []
priority: high
type: chore
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The qgis-rs compatibility package and its qgis_rs import shim are removed
- [ ] #2 No code, docs or config refers to @qgis-sdk/bridge, qgis-plugin, qgis-rs-py or qgis-node bins that no longer exist
- [ ] #3 pixi run gates is green after every removal
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Remove the compat package and its version-script and release entries, then sweep the repo with a grep allowlist and fix each stale reference it finds.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Done in 52cfc21: the qgis-rs compatibility package, its version and bun entries, and the qgis-sdk default style name are removed. Still open: the qgis-node npm name qgis-rs (renamed by TASK-58) and the qgis-sdk and qgis-plugin bins in qgis-node (removed by TASK-58).
<!-- SECTION:NOTES:END -->
