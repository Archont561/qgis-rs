---
id: TASK-33
title: Build the TypeScript QGIS bridge test harness
status: Done
assignee: []
created_date: '2026-10-03 09:16'
updated_date: '2026-10-05 20:24'
labels:
  - testing
  - typescript
  - bridge
  - fixtures
milestone: m-4
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
- [x] #1 BridgeHarness supports descriptions, scripted handlers, recorded target/method/argument calls, reply overrides, rejected calls, emitted events, reset, and restore.
- [x] #2 TypeScript facade tests use the harness transport and do not inspect _rawBridge internals.
- [x] #3 installBridgeGlobals restores every previous global and remains available for QWebChannel loader and description-loading tests.
- [x] #4 Shared assertions cover expected calls, structured error kinds, request IDs, event payloads, and callback/Promise normalization.
- [x] #5 fast-check properties cover request correlation, callback/Promise equivalence, JSON decoding, malformed responses, description/proxy consistency, fixture restoration, event subscription, and task progress.
- [x] #6 No test performs real network access, sleeps for fake tasks, or requires QWebEngine for ordinary bridge-client tests.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-05: Added createBridgeHarness to @qgis/test-utils (src/bridge-harness.ts). It builds the raw objects a QWebChannel would have handed over - one per target description - records every call as {target, method, args, requestId} with the trailing callback stripped, and answers from a script: on() computes an answer from the call, reply()/replyJson() pin one, reject() raises a structured BridgeHarnessError carrying the contract's error kind, and hold() queues calls so a test answers them out of order. Unscripted methods throw and name themselves rather than inventing an answer, because a harness that guesses lets a test assert against the harness instead of the client.

2026-10-05: installBridgeGlobals now takes optional objects and descriptions, defaulting to its built-in script, so harness.installGlobals() publishes the harness's own targets through the same global install the loader tests already use. One script drives both paths instead of two that can drift, and harness.restore() pops installations newest-first and is idempotent.

2026-10-05: Shared assertions (src/assertions.ts): expectCall, expectCallSequence, expectDistinctRequestIds, expectErrorKind, expectRejectedKind, expectEventPayloads, expectCallbackAndPromise and expectCallbackAndPromiseAgree. Shared fast-check arbitraries (src/arbitraries.ts): jsonValue, wireMethodName, errorKind, taskProgress, callArgs. bridge.test.ts dropped its private copy of the JSON generator and imports the shared one.

2026-10-05: Finding worth keeping - QgisBridge.call settles a caller-supplied callback with the RAW wire answer and its promise with the DECODED value. The two deliberately disagree, so the property states that relationship (one callback invocation, one resolution, JSON.parse of the first equals the second) rather than asserting equality. A second finding: a truncated JSON answer neither parses nor rejects; the decode is best-effort and the string survives, so a task handle degrades to task_id 'unknown'. Both are now pinned by tests instead of being folklore.

2026-10-05: Evidence - bun 47 to 119 across the two packages (@qgis/test-utils 14 to 37, @qgis-sdk/bridge 68 to 82); lint, typecheck and test green for both. No test opens a socket, waits on a timer or needs QWebEngine: facade tests construct LayersAPI/TasksAPI/MessageAPI/NetworkAPI directly over harness.target('qgis'), task progress arrives because the test emits it, and the three bridge-package property runs finish in ~190 ms total.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Facade tests now inject a scripted transport instead of installing globals and driving the loader to reach a facade. createBridgeHarness in @qgis/test-utils owns descriptions, call recording with request ids, scripted and held answers, structured rejections and events; shared assertions and fast-check arbitraries sit next to it so the same invariant is spelled once. installBridgeGlobals keeps its signature and its job for QWebChannel loader tests, and now accepts the harness's objects so both paths exercise one script. Eight properties cover request correlation under out-of-order answers, callback/promise settlement, JSON decoding, malformed answers, description/proxy closure, fixture restoration, event subscription and task progress.
<!-- SECTION:FINAL_SUMMARY:END -->
