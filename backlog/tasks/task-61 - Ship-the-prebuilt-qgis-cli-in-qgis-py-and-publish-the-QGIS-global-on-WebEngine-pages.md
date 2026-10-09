---
id: TASK-61
title: >-
  Ship the prebuilt qgis-cli in qgis-py and publish the QGIS global on WebEngine
  pages
status: Done
assignee: []
created_date: '2026-10-09 20:28'
updated_date: '2026-10-09 20:28'
labels:
  - enhancement
  - qgis-py
  - qgis-sdk
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Slice 6 of the restructure, plus the WebEngine global from the bridge vendoring.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 qgis-py wheels carry the prebuilt qgis-cli binary, staged per platform before maturin
- [x] #2 The qgis-cli console script runs that binary with the same arguments and exit status
- [x] #3 WebEngine pages get window.qgis, window.qgisBridge, window.qgisReady and one shared channel
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
c38f1be ships qgis-cli in the qgis-py wheel; 2cdd15d publishes window.qgis on WebEngine pages
<!-- SECTION:NOTES:END -->
