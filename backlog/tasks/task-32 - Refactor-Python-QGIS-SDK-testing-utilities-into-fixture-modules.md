---
id: TASK-32
title: Refactor Python QGIS SDK testing utilities into fixture modules
status: To Do
assignee: []
created_date: '2026-10-03 09:16'
updated_date: '2026-10-04 12:48'
labels:
  - testing
  - python
  - qgis-sdk
  - fixtures
milestone: m-4
dependencies:
  - TASK-31
documentation:
  - >-
    backlog/docs/testing/doc-5 -
    QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md
  - .knowledge/testing.md
  - .knowledge/qgis-plugin-ui.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Split qgis_sdk.testing behind compatibility exports into focused fixture modules for environment detection, calls, iface/actions, UI, bridge, network, tasks, processing data, and Hypothesis strategies. Preserve existing fixture names and public fake imports while making pure, Qt, QGIS, and WebEngine execution layers explicit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Existing qgis_sdk.testing imports and pytest fixture names remain backward compatible.
- [ ] #2 A shared Call/CallLog records iface, bridge, network, task, and UI calls through one observable shape.
- [ ] #3 FakeNetworkTransport supports scripted replies, failures, redirects, delays, response sequences, and request history without real network access.
- [ ] #4 FakeTaskManager models deterministic PENDING/RUNNING/SUCCESS/FAILURE/CANCELED transitions, progress, cancellation, callbacks, chains, and groups.
- [ ] #5 BridgeHarness validates request routing and serialization instead of directly exposing arbitrary fake methods.
- [ ] #6 Hypothesis strategies cover pure extents, zoom ranges, CRS auth IDs, plugin names, field specs, bridge requests, responses, and task transitions without generating live QGIS objects.
- [ ] #7 Pure-Python tests do not initialize Qt or QGIS, and failures to meet a Qt/QGIS prerequisite are explicit skips or prerequisite failures rather than fake fallbacks.
<!-- AC:END -->
