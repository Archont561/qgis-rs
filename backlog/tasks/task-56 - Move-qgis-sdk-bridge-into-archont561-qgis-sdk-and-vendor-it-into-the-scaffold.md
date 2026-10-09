---
id: TASK-56
title: Move qgis-sdk-bridge into @archont561/qgis-sdk and vendor it into the scaffold
status: In Progress
assignee: []
created_date: '2026-10-09 15:47'
updated_date: '2026-10-09 15:57'
labels:
  - qgis-sdk
  - bridge
dependencies: []
priority: high
type: enhancement
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The TypeScript bridge lives in ts-packages/qgis-sdk and is published as @archont561/qgis-sdk with typed subpath exports
- [ ] #2 The @qgis-sdk/bridge package and its ts-packages/qgis-sdk-bridge directory are removed, with no alias left behind
- [ ] #3 The Python scaffold copies the built bridge bundle into web/ only when a WebEngine UI is selected
- [ ] #4 bun run test, typecheck and lint pass for the moved package, and pixi run gates is green
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. git mv ts-packages/qgis-sdk-bridge to ts-packages/qgis-sdk and rename the package. 2. Point Python templates, codegen and tests at @archont561/qgis-sdk. 3. Update build, release and Biome config, then refresh bun.lock. 4. Update docs and READMEs. 5. Run the gates.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Done in 52cfc21: the package moved to ts-packages/qgis-sdk as @archont561/qgis-sdk, with 99 bun tests and 55 Python bridge tests passing and gates green. Still open: AC3, the scaffold copying the bridge bundle into web/ only for a WebEngine UI.
<!-- SECTION:NOTES:END -->
