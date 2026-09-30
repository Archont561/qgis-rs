---
id: TASK-17
title: Implement plugin packaging and repository publishing CLI
status: To Do
assignee: []
created_date: '2026-09-30 20:49'
labels:
  - qgis-sdk
  - cli
  - packaging
dependencies: []
documentation:
  - .knowledge/qgis-plugin-sdk.md
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement qgis-plugin package (creating compliant .zip archives with metadata and dependency wheels) and qgis-plugin publish (uploading to official QGIS Plugin Repository via API).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 qgis-plugin package validates metadata.txt, collects assets/bytecode, and produces installable .zip
- [ ] #2 Flag --all-targets bundles precompiled platform wheels for Rust-accelerated plugins
- [ ] #3 qgis-plugin publish supports token authentication, version bumping, and changelog verification
- [ ] #4 Packaging test validates generated ZIP structure against QGIS plugin specifications
<!-- AC:END -->
