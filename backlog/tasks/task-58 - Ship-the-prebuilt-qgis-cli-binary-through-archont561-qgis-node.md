---
id: TASK-58
title: Ship the prebuilt qgis-cli binary through @archont561/qgis-node
status: In Progress
assignee: []
created_date: '2026-10-09 15:47'
updated_date: '2026-10-09 16:08'
labels:
  - qgis-node
  - cli
dependencies: []
priority: high
type: enhancement
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 @archont561/qgis-node exposes an explicit qgis-cli bin that downloads the matching platform binary
- [ ] #2 The download is checked against a SHA-256 digest before it is run
- [ ] #3 The qgis-sdk and qgis-plugin bins are removed from qgis-node
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Rename the qgis-node npm package from qgis-rs to @archont561/qgis-node, and update the napi config, turbo tasks and the release list. 2. Remove the qgis-sdk and qgis-plugin bins from qgis-node. 3. bin/qgis-cli.js downloads the platform binary for the current OS and CPU from the release URL, verifies its SHA-256 digest, caches it, and runs it. 4. Export runCli(argv) returning { exitCode, stdout, stderr }. 5. Test the download and digest check with a local fixture server, then run the gates.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started. The code has not changed yet; the plan above is the first step.

Decision: use the @biomejs/biome model. @archont561/qgis-node lists one platform package per OS and CPU in optionalDependencies, for example @archont561/qgis-node-linux-x64, and the bin shim resolves the matching package. Nothing is downloaded at install or run time, so no release URL or network access is needed. Biome 2.5.15 lists eight platform packages, including musl variants. The first build covers linux-x64 only; other platforms are added in CI.
<!-- SECTION:NOTES:END -->
