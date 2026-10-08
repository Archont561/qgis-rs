---
id: TASK-18
title: Add frontend framework starter templates for WebEngine plugins
status: To Do
assignee: []
created_date: '2026-09-30 20:49'
updated_date: '2026-10-08 18:15'
labels:
  - qgis-sdk
  - ui
  - templates
  - web
milestone: m-3
dependencies:
  - TASK-44
documentation:
  - .knowledge/qgis-plugin-sdk.md
  - .knowledge/qgis-plugin-ui.md
  - >-
    backlog/docs/ui/doc-6 -
    QGIS-SDK-Native-UI-Kit-and-Visual-Design-Loop-Strategy.md
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Provide scaffold presets (--framework react, --framework vue, --framework svelte, --framework webcomponents) with preconfigured Vite builds and typed QWebChannel bridges.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 qgis-plugin new <name> --web --framework <fw> generates ready-to-build frontend setup in frontend/
- [ ] #2 Vite config builds to web/dist/ with relative asset links (base: ./)
- [ ] #3 TypeScript bridge bindings pre-imported and hooked into component lifecycle
- [ ] #4 Generated templates build successfully with Bun/Vite
- [ ] #5 Implement the framework presets in the canonical Rust command library. Python and Node entrypoints must invoke that implementation and must not fall back to Python template generation.
- [ ] #6 Generated snapshots verify each preset file manifest and confirm that --author and --email values are applied consistently in generated plugin code and metadata.txt.
<!-- AC:END -->
