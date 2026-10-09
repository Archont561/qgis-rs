---
id: TASK-60
title: 'Remove deprecated aliases, stale names and unpublished references'
status: In Progress
assignee: []
created_date: '2026-10-09 15:47'
updated_date: '2026-10-09 19:09'
labels:
  - cleanup
dependencies: []
priority: high
type: chore
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The qgis-rs compatibility package and its qgis_rs import shim are removed
- [ ] #2 No code, docs or config refers to @qgis-sdk/bridge, qgis-plugin, qgis-rs-py or qgis-node bins that no longer exist
- [ ] #3 pixi run gates is green after every removal
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Remove the compat package and its version-script and release entries, then sweep the repo with a grep allowlist and fix each stale reference it finds.

Slice 3 (repo rename): GitHub repository renamed to Archont561/qgis-rust; remote origin updated; repository URLs, the docs site base path and the repo prose now say qgis-rust. The crate API name qgis-rs is unchanged. The old repository path is a retired name for check-sources. Left on purpose: the prefix.dev channel @archont561/qgis-rs and PyPI trusted-publisher names, which are package identities.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Done in 52cfc21: the qgis-rs compatibility package, its version and bun entries, and the qgis-sdk default style name are removed. Still open: the qgis-node npm name qgis-rs (renamed by TASK-58) and the qgis-sdk and qgis-plugin bins in qgis-node (removed by TASK-58).

Slice 1 done: qgis-plugin binary, console script, conda entry and bin name dropped; qgis-sdk is the only CLI; boundary rule rejects non-canonical executables (xtask exempt). Gates green. AC2 still open for the stale-name sweep (slice 2).

Slice 2 done: check-sources now fails on retired names in tracked text (tests/retired_names.rs pins the matcher). The four named spellings are gone. Open question: the C++ namespace qgis_rs::native_manager is internal and not in AC2; decide whether to rename it to match qgis_sys before closing.

Slice 3 done: repository is Archont561/qgis-rust (gh reported 403 on the rename call, but the repo resolves under the new name with push permission; the old URL redirects). Gates exit 0 on c494d07.
<!-- SECTION:NOTES:END -->
