---
id: TASK-35
title: 'Separate Qt, QGIS, and WebEngine integration fixture gates'
status: To Do
assignee: []
created_date: '2026-10-03 09:16'
updated_date: '2026-10-04 12:48'
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
- [ ] #1 pure_python, qt, qgis, and webengine fixtures/markers select the intended environment without hidden fallback behavior.
- [ ] #2 Qt tests initialize QApplication once with QT_QPA_PLATFORM=offscreen and do not construct QWidget instances before application setup.
- [ ] #3 QGIS tests initialize and shut down QgsApplication deterministically, use the existing real fixtures, and run serialized.
- [ ] #4 WebEngine tests have a separate optional gate and do not become a dependency of ordinary bridge protocol tests.
- [ ] #5 The test documentation lists pure, fake-host, Qt, QGIS, WebEngine, and cross-language contract commands.
- [ ] #6 The full gate proves no global fixture leaks and preserves existing plugin behavior and golden values.
<!-- AC:END -->
