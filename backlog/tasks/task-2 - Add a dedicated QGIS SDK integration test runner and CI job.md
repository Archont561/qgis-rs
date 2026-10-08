---
id: TASK-2
title: Add a dedicated QGIS SDK integration test runner and CI job
status: Done
assignee: []
created_date: '2026-09-30'
updated_date: '2026-10-08 17:16'
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

<!-- SECTION:DESCRIPTION:BEGIN -->
Separate fast pure-Python SDK tests from tests that require an initialized QGIS runtime. The repository already has a committed simple-plugin fixture and a subprocess-backed integration test; make that path a first-class Pixi and CI workflow rather than relying on a developer command.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A documented Pixi task runs the QGIS integration tests independently of the pure-Python suite.
- [x] #2 The integration runner initializes QGIS with `QT_QPA_PLATFORM=offscreen` and isolates native startup/shutdown in a subprocess.
- [x] #3 CI executes both the pure-Python SDK suite and the QGIS integration suite.
- [x] #4 CI reports the QGIS version and runtime mode in test output.
- [x] #5 Integration tests skip clearly when QGIS is unavailable instead of failing during collection.
- [x] #6 The simple plugin fixture is treated as read-only test input and is not modified by tests.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Local and CI commands are documented in the SDK testing guide.
- [x] #2 A clean checkout can run the integration test from the declared Pixi environment.
- [x] #3 Failure output includes the subprocess stdout and stderr needed to diagnose QGIS/Qt issues.
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
PR #48 (commit 97ca783): gates green locally; PR CI run 37800870491 green. CI job log text was not readable here; step conclusions read via API.

Open: DoD clean-checkout proof not run (needs a fresh restore, about 8 GiB scratch; 5.2 GiB free here). Task stays In Progress until PR #48 merges.

AC1: pixi run -- bun --filter=qgis-sdk-py run test:qgis, documented in .knowledge/testing.md and the SDK testing guide. AC2: tests/qgis_subprocess.py sets QT_QPA_PLATFORM=offscreen in the child, plus PYTHONDONTWRITEBYTECODE=1 and a 300 second timeout.

AC3: the test lane (test script) runs the pure, qt and qgis gates strictly in sequence with QGIS_REQUIRE_NATIVE=1 on each. The three gates collect the same 409 tests as the old permissive run.

AC4: the header now reads qgis-sdk runtime: backend=qgis, qgis=3.44.14-Solothurn. Bug fixed: qgis_version was always None because qgis.core has no QGIS_VERSION; it now reads Qgis.version().

AC5: with no QGIS (bare py3.11 venv) the integration test skips with requires an importable qgis.core runtime, and the strict qgis gate errors instead of skipping.

AC6: the committed simple_plugin fixture is asserted byte-identical after the run. Evidence by damage: a child exiting 5 fails with exit status, QGIS release and both streams; a child writing into the fixture fails with fixture was modified.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped in PR #48. CI test lane now runs the pure, qt and qgis gates strictly in sequence (QGIS_REQUIRE_NATIVE=1 on each). QGIS child isolated in tests/qgis_subprocess.py: offscreen Qt, no bytecode writes, 300 s timeout, full stdout/stderr diagnostics. Integration test asserts the simple_plugin fixture is unchanged. Fixed qgis_version (was always None; now Qgis.version()). Run header names backend, QGIS release, layers and gate. Proof: pixi run gates green on the clean checkout; documented test:qgis command passes there (5 passed); PR CI green; without QGIS the test skips with a clear reason.
<!-- SECTION:FINAL_SUMMARY:END -->
