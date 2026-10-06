---
id: TASK-35
title: 'Separate Qt, QGIS, and WebEngine integration fixture gates'
status: Done
assignee: []
created_date: '2026-10-03 09:16'
updated_date: '2026-10-06 09:26'
labels:
  - testing
  - qt
  - qgis-sdk
  - integration
milestone: m-4
dependencies:
  - TASK-32
  - TASK-33
documentation:
  - >-
    backlog/docs/testing/doc-5 -
    QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md
  - .knowledge/testing.md
  - >-
    backlog/tasks/task-1 - Make the full QGIS SDK test suite headless and
    CI-green.md
  - >-
    backlog/tasks/task-2 - Add a dedicated QGIS SDK integration test runner and
    CI job.md
priority: medium
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make runtime requirements explicit across the Python SDK and TypeScript bridge suites. Keep pure tests independent of Qt/QGIS, run Qt tests offscreen, serialize real QGIS lifecycle tests, and isolate optional QWebEngine tests. Add fixture and marker documentation and gate commands.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 pure_python, qt, qgis, and webengine fixtures/markers select the intended environment without hidden fallback behavior.
- [x] #2 Qt tests initialize QApplication once with QT_QPA_PLATFORM=offscreen and do not construct QWidget instances before application setup.
- [x] #3 QGIS tests initialize and shut down QgsApplication deterministically, use the existing real fixtures, and run serialized.
- [x] #4 WebEngine tests have a separate optional gate and do not become a dependency of ordinary bridge protocol tests.
- [x] #5 The test documentation lists pure, fake-host, Qt, QGIS, WebEngine, and cross-language contract commands.
- [x] #6 The full gate proves no global fixture leaks and preserves existing plugin behavior and golden values.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The premise that needed fixing first: the suite already skipped a test whose
layer was missing, and that is the *right* default — but it makes the question
"does the QGIS layer actually work here?" unanswerable, because the run that
skipped every QGIS test is also green. So a gate was added as the strict
counterpart of the permissive default, under one rule: **a gate that skips is a
gate that proved nothing.** Asking for a layer this machine cannot reach is a
`pytest.UsageError`, not a skip.

`QGIS_TEST_LAYER=<pure|qt|qgis|webengine>` selects one layer. The selection
policy lives in a new `qgis_sdk.testing.gates` module that imports neither
pytest nor Qt — it is pure data and four functions, so it can be tested
directly instead of only through a subprocess. `plugin.py` keeps the pytest
wiring: resolve the gate in `pytest_configure`, stash it, deselect out-of-gate
tests in `pytest_collection_modifyitems`, then apply the pre-existing
missing-layer skip logic unchanged for the ungated run.

Four decisions worth recording:

- **`pure` is the absence of a layer marker, not the `pure_python` marker.**
  Defining it the other way left ~380 unmarked tests in no gate at all, which
  would have made the gates look clean while quietly testing nothing. Gates
  overlap on purpose (a test marked `qt` *and* `webengine` runs in both) but
  they cover the suite exhaustively.
- **`qgis_app` no longer always skips.** It now resolves in three steps: adopt
  a host's live `QgsApplication`, else construct one via the new `qgis_runtime`
  fixture **when the `qgis` gate is active**, else skip as before. Without this
  the `qgis` gate still skipped its one real consumer — measured, 3 passed /
  1 skipped. After: 4 passed. The default suite is untouched (still 4 skips).
- **The `qgis` gate refuses xdist with >1 worker.** `QgsApplication` is a
  process-wide singleton; parallel workers would share it. That is AC#3's
  "serialized", enforced rather than documented.
- **`qgis_lifecycle.py`, not `qgis_runtime.py`.** The module was originally
  named after the fixture, and the package's fixture re-export loop uses
  `setdefault` — so the submodule attribute won the name and the fixture
  silently vanished (`fixture 'qgis_runtime' not found`). Renaming the module
  fixed it, and `test_every_plugin_fixture_is_reachable_from_the_package`
  now fails loudly on any recurrence rather than waiting for a consumer.

`qgis_lifecycle.qgis_application()` adopts an existing application and does
**not** shut down a host's singleton; only an application it constructed is
`exitQgis()`-ed, in a `finally`. The long-standing "native teardown aborts
pytest" worry was checked out-of-process before any of this was written:
construct, `initQgis()`, `exitQgis()` exits 0 cleanly. The stderr noise during
a real QGIS start here (PDAL hdf5 plugin loads, Fontconfig, XDG_RUNTIME_DIR) is
pre-existing and benign.

Gate commands landed as four `test:<layer>` scripts in the package, and only
the ungated `test` is fanned out by turbo — that is the mechanism behind AC#4,
with the TS side confirmed clean (`ts-packages/qgis-sdk-bridge` references
QWebEngine only in an error string and a comment). Docs: a gate table and a
fixtures-by-layer table in `reference/testing.mdx`, a runnable section in
`guides/testing-fixtures.mdx`, the six-command table in `.knowledge/testing.md`,
and the gate list in the package README.

**Open item — the `webengine` gate has never gone green anywhere.** QtWebEngine
is not installed in this environment, so what is proven here is the *refusal*:
the gate exits 4 naming the reachable layers. That the gate selects and passes
real WebEngine tests remains unverified, and there are currently no
`@pytest.mark.webengine` tests to select. This is deliberately not counted as
proof.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:SUMMARY:BEGIN -->
Added strict per-layer test gates to the QGIS SDK suite: `QGIS_TEST_LAYER`
narrows a run to `pure`, `qt`, `qgis`, or `webengine` and errors when that layer
is unreachable, instead of skipping into a meaningless green.

Measured on the real suite: `pure` 388 passed / 3 skipped / 7 deselected, `qt`
3 passed / 395 deselected, `qgis` 4 passed / 394 deselected (it was 3 passed /
1 skipped before `qgis_app` was taught to build an application under the gate),
`webengine` a clean `UsageError`, and an unknown gate name likewise. The
ungated default run is 394 passed / 4 skipped — the same 4 skips as before the
change, with 41 new tests in `tests/test_layer_gates.py`.

New: `qgis_sdk.testing.gates` (pytest-free, Qt-free policy),
`qgis_sdk.testing.qgis_lifecycle` (constructs and shuts down a `QgsApplication`,
adopts without owning), the `qgis_runtime` fixture, four `test:<layer>` package
scripts, and documentation in the reference, the guide, `.knowledge/testing.md`
and the package README. The one unproven claim — a green `webengine` gate — is
recorded as an open item, not a checked box.
<!-- SECTION:SUMMARY:END -->
