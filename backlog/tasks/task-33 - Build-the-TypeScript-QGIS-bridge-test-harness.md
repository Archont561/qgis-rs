---
id: TASK-33
title: Build the TypeScript QGIS bridge test harness
status: To Do
assignee: []
created_date: '2026-10-03 09:16'
labels:
  - testing
  - typescript
  - bridge
  - fixtures
dependencies:
  - TASK-31
documentation:
  - >-
    backlog/docs/testing/doc-5 -
    QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md
  - ts-packages/test-utils/package.json
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend @qgis/test-utils with a scripted bridge transport and BridgeHarness. Use injected transports for feature-facade tests, keep installBridgeGlobals for loader/global integration tests, and centralize call recording, replies, errors, events, teardown, and property arbitraries.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 BridgeHarness supports descriptions, scripted handlers, recorded target/method/argument calls, reply overrides, rejected calls, emitted events, reset, and restore.
- [ ] #2 TypeScript facade tests use the harness transport and do not inspect _rawBridge internals.
- [ ] #3 installBridgeGlobals restores every previous global and remains available for QWebChannel loader and description-loading tests.
- [ ] #4 Shared assertions cover expected calls, structured error kinds, request IDs, event payloads, and callback/Promise normalization.
- [ ] #5 fast-check properties cover request correlation, callback/Promise equivalence, JSON decoding, malformed responses, description/proxy consistency, fixture restoration, event subscription, and task progress.
- [ ] #6 No test performs real network access, sleeps for fake tasks, or requires QWebEngine for ordinary bridge-client tests.
<!-- AC:END -->
