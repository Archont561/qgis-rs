---
id: TASK-58
title: Ship the prebuilt qgis-cli binary through @archont561/qgis-node
status: Done
assignee: []
created_date: '2026-10-09 15:47'
updated_date: '2026-10-10 08:12'
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
- [x] #3 The qgis-sdk and qgis-plugin bins are removed from qgis-node
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Rename the qgis-node npm package from qgis-rs to @archont561/qgis-node, and update the napi config, turbo tasks and the release list. 2. Remove the qgis-sdk and qgis-plugin bins from qgis-node. 3. bin/qgis-cli.js downloads the platform binary for the current OS and CPU from the release URL, verifies its SHA-256 digest, caches it, and runs it. 4. Export runCli(argv) returning { exitCode, stdout, stderr }. 5. Test the download and digest check with a local fixture server, then run the gates.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started. The code has not changed yet; the plan above is the first step.

Decision: use the @biomejs/biome model. @archont561/qgis-node lists one platform package per OS and CPU in optionalDependencies, for example @archont561/qgis-node-linux-x64, and the bin shim resolves the matching package. Nothing is downloaded at install or run time, so no release URL or network access is needed. Biome 2.5.15 lists eight platform packages, including musl variants. The first build covers linux-x64 only; other platforms are added in CI.

Landed: @archont561/qgis-node with Biome-model platform packages (linux-x64-gnu, linux-arm64-gnu, linux-x64-musl) holding bin/qgis-cli; runCli added; qgis-plugin and qgis-sdk bins removed; stage-cli script; 19 node tests pass; gates exit 0.

Still open: CI matrix builds for the other platforms, publishing platform packages in release.rs NPM_PACKAGES, win32 package not yet created.

Gap: qgis-cli is gitignored, so a fresh checkout has no staged binary and the qgis-node CLI tests fail under QGIS_REQUIRE_NATIVE=1 until scripts/stage-cli.js runs in the default env. Needs a CI or gates step that stages it.

Superseded: built-in qgis-cli removed from qgis-node in 41b02b4. ACs 1-2 no longer apply; AC 3 met. Left In Progress for owner decision to close.

Closed by owner decision. ACs 1-2 are superseded by D15 and by removing the built-in qgis-cli from qgis-node in 41b02b4, so they stay unchecked and are not work left to do. AC3 is checked. Still open, not in this task: the CI matrix that builds the other platforms, release.rs publishing of the platform packages, and the win32 package. Those need a new task before a release.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed as Done on the owner decision recorded in the 2026-10-10 session. The qgis-cli binary ships through @archont561/qgis-node as platform packages (linux-x64-gnu, linux-arm64-gnu, linux-x64-musl). The remaining platform and release work needs a new task.
<!-- SECTION:FINAL_SUMMARY:END -->
