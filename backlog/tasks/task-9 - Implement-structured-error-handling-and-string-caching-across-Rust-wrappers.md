---
id: TASK-9
title: Implement structured error handling and string caching across Rust wrappers
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
updated_date: '2026-10-03 08:31'
labels:
  - qgis
  - error-handling
  - performance
milestone: m-1
dependencies:
  - TASK-8
documentation:
  - .knowledge/qgis-vector-layer.md
  - .knowledge/decisions/D03-error-handling.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Replace silent boolean fallbacks in C++ shims with structured error retrieval via QgsError and QgisError (D03), and implement OnceCell caching for static string metadata (D06).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 C++ shims capture QgsError diagnostic messages on operation failure into thread-local error buffers
- [ ] #2 qgis::Error (QgisError) enum surfaces specific error categories and diagnostic strings
- [ ] #3 Static layer and CRS properties (authid, description) cache converted Rust Strings via OnceCell
- [ ] #4 Invalid layer paths return descriptive QgisError::InvalidLayer(msg) instead of generic boolean false
<!-- AC:END -->
