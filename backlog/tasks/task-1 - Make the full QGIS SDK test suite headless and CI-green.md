---
id: task-1
title: Make the full QGIS SDK test suite headless and CI-green
status: To Do
priority: high
assignee: []
created_date: '2026-09-30'
updated_date: '2026-09-30'
labels:
  - qgis-sdk
  - testing
dependencies: []
---

## Description

The focused SDK and subprocess-backed QGIS integration tests pass, but the full `sdk-test` run still aborts in the native Qt dialog test `test_ui.py::test_dialog_declarative`. Stabilize the Qt/QGIS test lifecycle so the complete SDK suite can run in a headless environment without native aborts or blocking dialogs.

## Acceptance Criteria

- [ ] `pixi run -e default sdk-test` completes with exit code 0 in the offscreen QGIS environment.
- [ ] Pure-Python execution continues to pass without importing or initializing QGIS.
- [ ] Qt dialog tests never invoke a blocking native dialog unexpectedly.
- [ ] QApplication and QgsApplication lifecycle is deterministic and does not segfault during pytest teardown.
- [ ] Environment-specific tests use the reusable `qgis_environment`, `qgis_app`, `qgis_available`, and `pure_python` fixtures or the `qgis`/`pure_python` markers.
- [ ] The fixture-backed simple-plugin integration test remains green.

## Definition of Done

- [ ] Full SDK tests pass in the QGIS/offscreen environment.
- [ ] Full SDK tests pass in a pure-Python environment, with expected QGIS skips.
- [ ] The test lifecycle and native teardown decision are documented in the SDK testing guide.
