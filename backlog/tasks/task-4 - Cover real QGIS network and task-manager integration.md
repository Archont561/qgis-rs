---
id: TASK-4
title: Cover real QGIS network and task-manager integration
status: To Do
assignee: []
created_date: '2026-09-30'
updated_date: '2026-10-03 08:31'
labels:
  - qgis-sdk
  - network
  - tasks
milestone: m-3
dependencies:
  - TASK-2
documentation:
  - .knowledge/qgis-plugin-sdk.md
  - .knowledge/qgis-plugin-ui.md
  - .knowledge/testing.md
priority: medium
---

## Description

The current tests cover request and task behavior with fakes and pure-Python fallbacks. Add deterministic QGIS-runtime coverage for the native network manager and task manager without depending on external services or unstable global state.

## Acceptance Criteria

- [ ] A local HTTP test server exercises a QGIS-backed network request without internet access.
- [ ] Retry status handling, retry history, headers, and JSON decoding are verified through the decorated session API.
- [ ] A real QgsTaskManager test covers task submission, completion, cancellation, and result retrieval.
- [ ] Fluent signatures/chains are tested against both the fallback manager and the QGIS manager where supported.
- [ ] Tests do not share a global network manager, task manager, or Processing provider between cases.
- [ ] Native QGIS tests run in a subprocess or a documented QGIS host lifecycle and do not leave worker threads alive.

## Definition of Done

- [ ] Network and task integration tests pass deterministically in the QGIS CI job.
- [ ] No external network access is required.
- [ ] The fallback tests remain runnable in a bare Python environment.
