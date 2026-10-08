---
id: TASK-51
title: Unify TypeScript QGIS facade calls behind a typed transport adapter
status: Done
assignee: []
created_date: '2026-10-08 18:14'
updated_date: '2026-10-08 19:45'
labels:
  - typescript
  - bridge
  - refactor
dependencies: []
references:
  - ts-packages/qgis-sdk-bridge/src/qgis/iface.ts
  - ts-packages/qgis-sdk-bridge/src/qgis/layers.ts
  - ts-packages/qgis-sdk-bridge/src/qgis/message.ts
  - ts-packages/qgis-sdk-bridge/src/qgis/network.ts
  - ts-packages/qgis-sdk-bridge/src/qgis/processing.ts
  - ts-packages/qgis-sdk-bridge/src/qgis/project.ts
  - ts-packages/qgis-sdk-bridge/src/qgis/settings.ts
  - ts-packages/qgis-sdk-bridge/src/qgis/tasks.ts
  - ts-packages/qgis-sdk-bridge/tests/harness.test.ts
documentation:
  - >-
    backlog/docs/refactor/doc-3 -
    Repository-Refactor-and-Test-Modernization-Plan.md
  - .agents/skills/tdd/SKILL.md
  - .agents/skills/refactor/SKILL.md
priority: medium
type: task
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The eight TypeScript QGIS facade modules repeat raw QWebChannel callback invocation, Promise and error wrapping, bridge-method lookup, and missing-transport handling. Their response decoding and fallback results differ and are externally observable. Add characterization coverage through the existing injected bridge harness, then extract a narrow typed call and transport adapter while preserving each facade public behavior. This implements P1.8 of the repository refactor plan. TASK-33 already provides the harness and must be reused.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Agree public test seams with the user before writing tests. Exercise exported facade methods through createBridgeHarness rather than private fields or _call helpers.
- [x] #2 Extend behavior tests first. Characterize wire names, argument order and defaults, callback rejection, JSON decoding, bridge fallback, and missing-transport behavior across all eight facades. Reuse existing coverage.
- [x] #3 Extract a narrow typed adapter for transport invocation and callback and Promise normalization while keeping facade public methods, exports, and return types stable.
- [x] #4 Preserve per-facade decoding and fallback semantics including best-effort JSON parsing, message boolean coercion, network browser-fetch fallback, mock values, warnings, and error propagation. Keep the adapter typed and avoid an untyped catch-all API.
- [x] #5 Run @qgis-sdk/bridge tests, typecheck, and lint through the repository Pixi workflow. Leave the task open until verified.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Treat the exported methods of the eight QGIS facades as the agreed public seams. Exercise them only through createBridgeHarness, observing wire calls, returned values or rejections, warnings, and browser-fetch fallback; do not test private helpers or fields. Add one characterization slice at a time, record the focused red where shared behavior is missing, extract a narrow typed callback/Promise transport adapter, migrate each facade incrementally without changing facade-specific decoding or fallbacks, then verify package tests, typecheck, lint, and the applicable repository gate through Pixi.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-08: The user pre-agreed the public seams in the task prompt: exported facade methods exercised through createBridgeHarness, with no private _call or field assertions. The pre-production focused baseline was 14 passing harness tests. Added characterization slices one at a time; all passed against the duplicated implementation, so coverage exposed no missing behavior and no artificial failing test was introduced.

2026-10-08: Added operation coverage for all eight facades, including wire names, argument order/defaults, raw callback errors, Promise bridge fallback/rejection, best-effort JSON behavior, message coercion, missing-transport mocks/logs/warnings, and a stubbed browser-fetch success/error path. Extracted qgis/transport.ts: each facade provides a finite operation interface and typed fallback map; callback decode mode is explicit per call and bridge Promise results are not re-decoded. Migrated message, iface, settings, project, processing, layers, tasks, and network incrementally, rerunning focused tests and typecheck after each slice.

2026-10-08 package evidence through Pixi: focused harness 26 passed; full @qgis-sdk/bridge 99 passed; typecheck exited 0; lint exited 0 (126 pre-existing noExplicitAny warnings remain non-fatal); build exited 0. Repository gate still pending, so AC #5 and status remain open.

2026-10-08 repository evidence: pixi run gates passed on commit fdeddcf, including source/boundary checks, format drift, package lint, the full test fan-out, builds, and package checks.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Introduced a finite-operation QgisTransportAdapter that normalizes QWebChannel callbacks and bridge Promise methods while leaving each facade in charge of its decode mode and missing-transport policy. Migrated all eight QGIS facades without changing exported method signatures, defaults, response helpers, warnings, fallback values, or errors. Expanded createBridgeHarness behavior coverage from 14 to 26 focused tests and verified 99 full bridge-package tests, typecheck, lint, build, and the repository gate through Pixi.
<!-- SECTION:FINAL_SUMMARY:END -->
