---
id: TASK-12
title: Bind QgsMapSettings and QgsMapRendererSequentialJob for embedded rendering
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
labels:
  - qgis-sys
  - rendering
  - qgis-render
dependencies:
  - TASK-10
documentation:
  - .knowledge/decisions/D08-standalone-rendering-app.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement headless C++ map rendering via QgsMapSettings and synchronous QgsMapRendererSequentialJob::waitForFinished(), extracting rendered image pixels from QImage.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 C++ shims configure QgsMapSettings (layers, extent, size, DPI, background color)
- [ ] #2 QgsMapRendererSequentialJob runs synchronous render via waitForFinished without Qt signals
- [ ] #3 Rendered QImage output is exported to PNG/JPEG byte buffers
- [ ] #4 Standalone rendering test renders a styled .qgs/.qgz project to a valid PNG in offscreen mode
<!-- AC:END -->
