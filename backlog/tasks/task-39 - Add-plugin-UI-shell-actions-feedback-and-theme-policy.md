---
id: TASK-39
title: 'Add plugin UI shell, actions, feedback, and theme policy'
status: To Do
assignee: []
created_date: '2026-10-03 09:19'
updated_date: '2026-10-04 12:48'
labels:
  - qgis-sdk
  - ui
  - plugin
  - theme
milestone: m-3
dependencies:
  - TASK-36
documentation:
  - >-
    backlog/docs/ui/doc-6 -
    QGIS-SDK-Native-UI-Kit-and-Visual-Design-Loop-Strategy.md
  - .knowledge/qgis-plugin-sdk.md
  - .knowledge/qgis-plugin-ui.md
priority: medium
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add the plugin-host layer for menus, toolbars, shortcuts, icons, docks, status messages, notifications, task feedback, cancellation, lifecycle cleanup, QGIS palette, high-DPI, density, focus, keyboard navigation, and accessibility policy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Actions, menus, toolbars, shortcuts, icons, docks, and plugin-owned settings have public helpers with deterministic cleanup on unload.
- [ ] #2 Feedback integrates with the task system for progress, cancellation, logs, warnings, errors, completion, and retry without blocking the GUI thread.
- [ ] #3 The UI shell can be tested with fake iface/action/task fixtures without Qt or QGIS.
- [ ] #4 Native QGIS palette, spacing, density, high-DPI, keyboard focus, and accessibility rules are applied without a parallel CSS framework.
- [ ] #5 Plugin unload removes registered actions, docks, signals, and owned resources exactly once.
- [ ] #6 Long-running work uses task APIs and never runs synchronously on the GUI thread.
<!-- AC:END -->
