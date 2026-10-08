---
id: TASK-53
title: Dispatch QGIS EventTarget signals exactly once
status: To Do
assignee: []
created_date: '2026-10-08 18:14'
labels:
  - typescript
  - bridge
  - bug
dependencies: []
references:
  - ts-packages/qgis-sdk-bridge/src/qgis.ts
  - ts-packages/qgis-sdk-bridge/tests/bridge.test.ts
documentation:
  - .agents/skills/tdd/SKILL.md
priority: medium
type: bug
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
QgisAPI._wireSignals registers forwarding listeners in its constructor, and createQgisBridge registers listeners for the same four signals again. One bridge event can therefore produce two notifications on the public qgis EventTarget for layer_added, layer_removed, task_progress, and task_finished. Existing coverage only asserts that one event listener ran, so it does not detect the duplicate delivery.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Agree the public event test seam with the user before writing the regression test. Use createQgisBridge or the exported QgisAPI surface and assert event counts rather than a boolean called flag.
- [ ] #2 Add a failing behavior test showing one bridge event for layer_added, layer_removed, task_progress, and task_finished results in exactly one qgis EventTarget notification with the original detail.
- [ ] #3 Remove the duplicate forwarding path while preserving signal names, details, and the existing single delivery for message.
- [ ] #4 Run the @qgis-sdk/bridge package tests, typecheck, and lint through the repository Pixi workflow. Leave the task open until verified.
<!-- AC:END -->
