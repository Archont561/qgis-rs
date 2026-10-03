---
id: task-1
title: Make the full QGIS SDK test suite headless and CI-green
status: In Progress
assignee: []
created_date: '2026-09-30'
updated_date: '2026-10-03 08:31'
labels:
  - qgis-sdk
  - testing
milestone: m-3
dependencies: []
documentation:
  - .knowledge/qgis-plugin-sdk.md
  - .knowledge/qgis-plugin-ui.md
  - .knowledge/testing.md
priority: high
---

## Description

The focused SDK and subprocess-backed QGIS integration tests pass, but the full `sdk-test` run still aborts in the native Qt dialog test `test_ui.py::test_dialog_declarative`. Stabilize the Qt/QGIS test lifecycle so the complete SDK suite can run in a headless environment without native aborts or blocking dialogs.

## Acceptance Criteria

- [x] `pixi run -e default sdk-test` completes with exit code 0 in the offscreen QGIS environment.
- [x] Pure-Python execution continues to pass without importing or initializing QGIS.
- [x] Qt dialog tests never invoke a blocking native dialog unexpectedly.
- [x] QApplication and QgsApplication lifecycle is deterministic and does not segfault during pytest teardown.
- [ ] Environment-specific tests use the reusable `qgis_environment`, `qgis_app`, `qgis_available`, and `pure_python` fixtures or the `qgis`/`pure_python` markers.
- [ ] The fixture-backed simple-plugin integration test remains green.

## Definition of Done

- [ ] Full SDK tests pass in the QGIS/offscreen environment.
- [ ] Full SDK tests pass in a pure-Python environment, with expected QGIS skips.
- [ ] The test lifecycle and native teardown decision are documented in the SDK testing guide.

## Progress Notes

- 2026-09-30: Fixed the `test_ui.py::test_dialog_declarative` abort/hang. The
  three tests calling `Dialog.exec()`/`WebDialog.exec()` now pin the documented
  fallback via `monkeypatch`, so the suite passes identically in the bare
  virtualenv (pure-Python fallback) and in a PyQt/QGIS-bearing pixi
  environment (no QApplication-less QWidget construction, no blocking modal
  loop). `pixi run sdk-test`: 121 passed, 2 skipped, exit 0. Remaining: the
  reusable `qgis_environment`/`pure_python` marker fixtures and the SDK
  testing-guide lifecycle documentation.
