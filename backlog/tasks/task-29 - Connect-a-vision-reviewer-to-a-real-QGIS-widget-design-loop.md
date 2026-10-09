---
id: TASK-29
title: Connect a vision reviewer to a real QGIS widget design loop
status: To Do
assignee: []
created_date: '2026-10-03 08:50'
updated_date: '2026-10-09 00:10'
labels:
  - qgis-sdk
  - ui
  - agent
  - visual-testing
milestone: m-3
dependencies:
  - TASK-28
  - TASK-36
documentation:
  - .knowledge/qgis-ui-agent-design-loop.md
  - >-
    backlog/docs/ui/doc-9 -
    Agent-Driven-PyQt-QGIS-Visual-Design-Loop-Spec.md
  - >-
    backlog/docs/ui/doc-10 -
    qgis-sdk-UI-Preview-CLI-and-Dev-Loop.md
  - >-
    backlog/docs/ui/doc-6 -
    QGIS-SDK-Native-UI-Kit-and-Visual-Design-Loop-Strategy.md
  - >-
    backlog/docs/testing/doc-5 -
    QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md
priority: medium
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Promote the feasibility probe into an optional QGIS SDK visual-design workflow. Render one real qgis_sdk.ui.Dialog or plugin widget in the restored Pixi/QGIS environment, capture it headlessly, send the screenshot to a vision-capable reviewer, validate the returned visual spec, and require human approval before changing scaffold/template output.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A real qgis.PyQt widget factory reuses the existing QApplication/QgsApplication lifecycle and runs serialized with QT_QPA_PLATFORM=offscreen.
- [ ] #2 The workflow captures PNG and JSON evidence for each bounded iteration and produces a reviewable final diff.
- [ ] #3 The reviewer adapter accepts image plus constraints and returns schema-validated visual parameters only; malformed or behavioral edits fail closed.
- [ ] #4 Widget behavior, signals, QGIS access, task execution, and bridge behavior remain covered by ordinary fixture-driven tests.
- [ ] #5 The workflow runs in the restored Pixi QGIS environment and is documented without making model credentials a test prerequisite.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implement the design loop specified in backlog/docs/ui/doc-9: use the native-first UI contract and typed widget specs from TASK-36; render one real qgis_sdk.ui.Dialog or plugin widget; capture with QWidget.grab; analyze constraints; route optional vision review through validated JSON only; require human approval before template changes.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The UI design system dependency is TASK-36. The TASK-28 feasibility probe was removed from the repository; its validated design and evidence are captured in backlog/docs/ui/doc-9 and the knowledge entry. This task builds the loop per that spec against a real QGIS/PyQt widget and adds optional vision review.

2026-10-09: the human-facing preview command ships first as TASK-54 (doc-10 — `qgis-sdk ui preview` with browser forwarding and a `/events` interaction channel); this task's loop converges with it under doc-9's run contract.
<!-- SECTION:NOTES:END -->
