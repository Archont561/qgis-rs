---
id: TASK-36
title: Define the native-first declarative QGIS SDK UI contract
status: To Do
assignee: []
created_date: '2026-10-03 09:19'
updated_date: '2026-10-04 12:48'
labels:
  - qgis-sdk
  - ui
  - api
  - design
milestone: m-3
dependencies:
  - TASK-3
documentation:
  - >-
    backlog/docs/ui/doc-6 -
    QGIS-SDK-Native-UI-Kit-and-Visual-Design-Loop-Strategy.md
  - .knowledge/qgis-plugin-ui.md
  - .knowledge/qgis-plugin-sdk.md
priority: high
type: task
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define and characterize the public qgis_sdk.ui contract for a native-first declarative plugin UI kit. Cover Dialog, Panel, Dock, Form, Section, Tabs, ActionBar, field specifications, typed values, validation, state, actions, feedback, theme policy, and explicit Qt/QGIS/WebEngine boundaries. Preserve current public imports while recording the target behavior.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The public UI contract distinguishes declarative specs, typed field values, Qt rendering, QGIS widget adapters, plugin actions, feedback, state persistence, theme, and optional WebEngine.
- [ ] #2 The MVP field catalog covers text, multiline, integer, number, boolean, choice, file, folder, color, date/time, layer, field, CRS, extent, expression, feature source, map scale, and raster band as supported or explicitly deferred.
- [ ] #3 Dialog, Panel, Dock, Form, Section, Tabs, ActionBar, loading, empty, and error states have characterization examples.
- [ ] #4 Processing parameter definitions remain owned by QGIS and the SDK does not introduce a competing Processing UI model.
- [ ] #5 Native QGIS palette, high-DPI, keyboard focus, accessibility, spacing, and density rules are documented as testable policy.
- [ ] #6 Missing Qt/QGIS behavior is explicit and does not report a failed UI construction as accepted.
<!-- AC:END -->
