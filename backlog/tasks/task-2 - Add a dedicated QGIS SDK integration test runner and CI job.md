---
id: TASK-2
title: Add a dedicated QGIS SDK integration test runner and CI job
status: To Do
assignee: []
created_date: '2026-09-30'
updated_date: '2026-10-03 08:31'
labels:
  - qgis-sdk
  - ci
  - testing
milestone: m-3
dependencies:
  - TASK-1
documentation:
  - .knowledge/qgis-plugin-sdk.md
  - .knowledge/qgis-plugin-ui.md
  - .knowledge/testing.md
priority: high
---

## Description

Separate fast pure-Python SDK tests from tests that require an initialized QGIS runtime. The repository already has a committed simple-plugin fixture and a subprocess-backed integration test; make that path a first-class Pixi and CI workflow rather than relying on a developer command.

## Acceptance Criteria

- [ ] A documented Pixi task runs the QGIS integration tests independently of the pure-Python suite.
- [ ] The integration runner initializes QGIS with `QT_QPA_PLATFORM=offscreen` and isolates native startup/shutdown in a subprocess.
- [ ] CI executes both the pure-Python SDK suite and the QGIS integration suite.
- [ ] CI reports the QGIS version and runtime mode in test output.
- [ ] Integration tests skip clearly when QGIS is unavailable instead of failing during collection.
- [ ] The simple plugin fixture is treated as read-only test input and is not modified by tests.

## Definition of Done

- [ ] Local and CI commands are documented in the SDK testing guide.
- [ ] A clean checkout can run the integration test from the declared Pixi environment.
- [ ] Failure output includes the subprocess stdout and stderr needed to diagnose QGIS/Qt issues.
