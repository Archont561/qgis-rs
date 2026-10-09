---
id: TASK-44
title: Package the Rust-native qgis-plugin and qgis-sdk CLI
status: To Do
assignee: []
created_date: '2026-10-03 09:35'
updated_date: '2026-10-09 21:55'
labels:
  - qgis-sdk
  - cli
  - rust
  - packaging
  - testing
milestone: m-3
dependencies:
  - TASK-26
  - TASK-42
  - TASK-43
documentation:
  - >-
    backlog/docs/architecture/doc-7 -
    Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md
  - >-
    backlog/tasks/task-26 -
    Refactor-qgis-sdk-CLI-onto-the-shared-Rust-engine-wire-protocol.md
  - .agents/skills/refactor/SKILL.md
  - .agents/skills/tdd/SKILL.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ship one canonical Rust plugin-development CLI through Python and optional Node distributions. qgis-plugin is canonical; qgis-sdk is an exact alias. Package launchers preserve arguments, stdout, stderr, signals, and exit status and never implement an alternate fallback.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 qgis-plugin and qgis-sdk call one shared Rust command library and have identical command behavior
- [ ] #2 qgis-sdk Python console scripts and npm bin wrappers locate and execute the canonical binary or fail with a clear installation error
- [ ] #3 Scaffold, validate, build, test, package, bridge, rust, install, dev, and publish commands have stable machine-readable contracts
- [ ] #4 QGIS integration commands launch controlled offscreen QGIS/Python processes with explicit runtime requirements and cancellation
- [ ] #5 Package manifests, wheels, npm artifacts, checksums, and release checks verify the binaries and generated files
- [ ] #6 CLI tests cover stdout/stderr/exit codes, subprocess signals, filesystem boundaries, generated snapshots, and no duplicate fallback semantics
- [ ] #7 Generated-file snapshots verify that supplied or default author and email values are applied consistently to generated plugin code and metadata.txt for every scaffold mode supported by the canonical Rust CLI.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Superseded (2026-10). qgis-plugin is dropped and qgis-sdk is pure Python, so there is no Rust binary to package. The qgis-cli binary packaging moves to TASK-58, and the zip packaging moves to TASK-57.

Decision: keep the crates/qgis-sdk crate. The qgis-sdk wheel ships the built Rust binary, and the Python qgis-sdk main forwards argv, stdout, stderr, signals and exit status to it. No Python fallback re-implements commands. qgis-sdk is the only command name; qgis-plugin is not part of this task.

Superseded: the qgis-sdk crate is being removed, not kept. qgis-sdk is a pure-Python CLI (TASK-57, typer and questionary). qgis-plugin references are removed from live files.
<!-- SECTION:NOTES:END -->
