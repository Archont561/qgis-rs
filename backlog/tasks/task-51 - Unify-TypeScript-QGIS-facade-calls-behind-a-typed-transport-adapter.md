---
id: TASK-51
title: Unify TypeScript QGIS facade calls behind a typed transport adapter
status: To Do
assignee: []
created_date: '2026-10-08 18:14'
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
- [ ] #1 Agree public test seams with the user before writing tests. Exercise exported facade methods through createBridgeHarness rather than private fields or _call helpers.
- [ ] #2 Extend behavior tests first. Characterize wire names, argument order and defaults, callback rejection, JSON decoding, bridge fallback, and missing-transport behavior across all eight facades. Reuse existing coverage.
- [ ] #3 Extract a narrow typed adapter for transport invocation and callback and Promise normalization while keeping facade public methods, exports, and return types stable.
- [ ] #4 Preserve per-facade decoding and fallback semantics including best-effort JSON parsing, message boolean coercion, network browser-fetch fallback, mock values, warnings, and error propagation. Keep the adapter typed and avoid an untyped catch-all API.
- [ ] #5 Run @qgis-sdk/bridge tests, typecheck, and lint through the repository Pixi workflow. Leave the task open until verified.
<!-- AC:END -->
