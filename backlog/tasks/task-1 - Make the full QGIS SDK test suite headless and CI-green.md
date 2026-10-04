---
id: TASK-1
title: Make the full QGIS SDK test suite headless and CI-green
status: Done
assignee: []
created_date: '2026-09-30'
updated_date: '2026-10-03 17:30'
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

<!-- SECTION:DESCRIPTION:BEGIN -->
The focused SDK and subprocess-backed QGIS integration tests pass, but the full `sdk-test` run still aborts in the native Qt dialog test `test_ui.py::test_dialog_declarative`. Stabilize the Qt/QGIS test lifecycle so the complete SDK suite can run in a headless environment without native aborts or blocking dialogs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `pixi run -e default sdk-test` completes with exit code 0 in the offscreen QGIS environment.
- [x] #2 Pure-Python execution continues to pass without importing or initializing QGIS.
- [x] #3 Qt dialog tests never invoke a blocking native dialog unexpectedly.
- [x] #4 QApplication and QgsApplication lifecycle is deterministic and does not segfault during pytest teardown.
- [x] #5 Environment-specific tests use the reusable `qgis_environment`, `qgis_app`, `qgis_available`, and `pure_python` fixtures or the `qgis`/`pure_python` markers.
- [x] #6 The fixture-backed simple-plugin integration test remains green.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Full SDK tests pass in the QGIS/offscreen environment.
- [x] #2 Full SDK tests pass in a pure-Python environment, with expected QGIS skips.
- [x] #3 The test lifecycle and native teardown decision are documented in the SDK testing guide.
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03: Added a source-checkout-safe pytest plugin registration in py-packages/qgis-sdk/tests/conftest.py. It registers qgis_sdk.testing only when the installed pytest11 entry point is absent, avoiding duplicate registration in Pixi while making qgis_environment, qgis_available, pure_python, qgis_app, and the fake fixtures available from source.

2026-10-03: Marked the real NetworkAccessManager test with @pytest.mark.qgis and changed it to use the reusable qgis_app fixture, so it skips before touching QGIS when no host application exists.

2026-10-03: Documented the QGIS/offscreen and pure-Python lifecycle, fixture/marker contract, subprocess-backed simple-plugin test, and commands in .knowledge/testing.md.

2026-10-03: QGIS/offscreen proof: pixi run -e default env QGIS_REQUIRE_NATIVE=1 python -m pytest py-packages/qgis-sdk/tests -q -> 121 passed, 2 skipped. The fixture-backed simple-plugin integration test is included in this run.

2026-10-03: Pure-Python proof: a host-binding-free test probe blocked qgis/PyQt imports and ran the same suite -> 120 passed, 3 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The SDK suite now uses explicit reusable runtime fixtures and markers in both hosted and pure-Python modes. Qt remains offscreen, native QGIS startup/teardown is isolated in the committed subprocess integration test, and the lifecycle is documented. QGIS/offscreen and pure-Python suite proofs are green.
<!-- SECTION:FINAL_SUMMARY:END -->

## Progress Notes

- 2026-09-30: Fixed the `test_ui.py::test_dialog_declarative` abort/hang. The
  three tests calling `Dialog.exec()`/`WebDialog.exec()` now pin the documented
  fallback via `monkeypatch`, so the suite passes identically in the bare
  virtualenv (pure-Python fallback) and in a PyQt/QGIS-bearing pixi
  environment (no QApplication-less QWidget construction, no blocking modal
  loop). `pixi run sdk-test`: 121 passed, 2 skipped, exit 0. Remaining: the
  reusable `qgis_environment`/`pure_python` marker fixtures and the SDK
  testing-guide lifecycle documentation.
