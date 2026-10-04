---
id: TASK-9
title: Implement structured error handling and string caching across Rust wrappers
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
updated_date: '2026-10-04 12:48'
labels:
  - qgis
  - error-handling
  - performance
  - deprecated
milestone: m-1
dependencies: []
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
