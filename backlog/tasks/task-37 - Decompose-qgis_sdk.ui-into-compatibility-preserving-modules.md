---
id: TASK-37
title: Decompose qgis_sdk.ui into compatibility-preserving modules
status: To Do
assignee: []
created_date: '2026-10-03 09:19'
labels:
  - qgis-sdk
  - ui
  - refactor
  - qt
dependencies:
  - TASK-36
documentation:
  - >-
    backlog/docs/ui/doc-6 -
    QGIS-SDK-Native-UI-Kit-and-Visual-Design-Loop-Strategy.md
  - .agents/skills/refactor/SKILL.md
  - .knowledge/qgis-plugin-ui.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Split the current qgis_sdk.ui module behind stable public exports. Extract specs, fields, forms, dialogs, panels, QGIS widgets, actions, feedback, state, theme, Qt backend, and optional WebEngine responsibilities. Use characterization tests before each extraction and preserve current Dialog, field, layout, Button, WebDialog, and bridge imports.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 qgis_sdk.ui public imports remain backward compatible throughout the refactor.
- [ ] #2 Declarative specifications can be constructed and validated without importing Qt or QGIS.
- [ ] #3 Qt construction is routed through the existing _qt funnel and no module adds a second binding-detection path.
- [ ] #4 Dialog, WebDialog, fallback, persistence, and lifecycle behavior are covered before structural extraction.
- [ ] #5 Failures to construct a real UI raise or skip explicitly; they do not print an error and return Dialog.Accepted.
- [ ] #6 Each extraction has pure, fake-host, Qt, and optional WebEngine verification as appropriate.
<!-- AC:END -->
