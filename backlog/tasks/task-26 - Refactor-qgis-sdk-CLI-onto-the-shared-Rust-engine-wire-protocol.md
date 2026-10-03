---
id: TASK-26
title: Refactor qgis-sdk CLI onto the shared Rust engine wire protocol
status: To Do
assignee: []
created_date: '2026-10-03 01:51'
updated_date: '2026-10-03 09:37'
labels:
  - qgis-sdk
  - qgis-py
  - qgis-engine
  - qgis-protocol
  - cli
  - architecture
  - refactor
milestone: m-3
dependencies:
  - TASK-40
references:
  - crates/qgis-protocol
  - crates/qgis-engine
  - crates/qgis-py
  - crates/qgis-sdk
  - py-packages/qgis-sdk/src/qgis_sdk/cli.py
  - py-packages/qgis-sdk/src/qgis_sdk/_fallback_cli.py
documentation:
  - crates/qgis-protocol
  - crates/qgis-engine
  - crates/qgis-py
  - crates/qgis-py/ARCHITECTURE.md
  - crates/qgis-sdk
  - py-packages/qgis-sdk/src/qgis_sdk/cli.py
  - py-packages/qgis-sdk/src/qgis_sdk/_fallback_cli.py
  - .knowledge/api-design.md
  - .knowledge/architecture.md
  - .knowledge/qgis-plugin-sdk.md
  - .knowledge/decisions/D09-wire-protocol-over-ffi.md
  - .knowledge/decisions/D13-rust-cli-ffi-and-qgis-sdk-boundaries.md
  - >-
    backlog/docs/architecture/doc-7 -
    Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md
  - .agents/skills/refactor/SKILL.md
  - .agents/skills/tdd/SKILL.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Refactor the `qgis-sdk` Python package's CLI so its command behavior is implemented once in Rust behind an engine + versioned JSON wire protocol, instead of being duplicated in Python and silently falling back to `_fallback_cli.py`.

The current package has three overlapping paths: Python command handlers in `py-packages/qgis-sdk/src/qgis_sdk/cli.py`, a pure-Python `_fallback_cli.py`, and Rust CLI implementations in `crates/qgis-sdk/src/bin/qgis-plugin.rs` plus the incomplete sibling-delegating `qgis-sdk.rs`. In contrast, `crates/qgis-py` already follows D09 with one `invoke(request_json) -> response_json` binding over `qgis-protocol` and `qgis-engine`.

First settle the architecture rather than assuming that every SDK command belongs in the existing render engine: evaluate (a) extending the qgis-py protocol/engine with a namespaced CLI-invocation surface versus (b) a separate qgis-sdk protocol/engine pair embedded by the qgis-sdk crate, while sharing the envelope/version/error conventions wherever that is sound. Record the choice and its boundaries in a decision record. The selected design must maximize Rust reuse, keep Python as a thin client, and make the CLI path independent of PyQGIS; plugin runtime/UI code that intentionally runs inside QGIS is outside this CLI boundary.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An architecture decision record compares an enhanced qgis-py/qgis-engine protocol with a separate qgis-sdk protocol/engine, selects one, and defines operation namespacing, transport versioning, payload/result/error shapes, and the boundary between CLI workflows and QGIS-hosted plugin runtime.
- [ ] #2 The selected Rust engine owns the qgis-sdk CLI behavior and exposes a versioned JSON invoke entry point; qgis-plugin and qgis-sdk binaries reuse the same library/engine without sibling subprocess delegation, duplicated command dispatch, or a minimal behavior-only alias.
- [ ] #3 The Python qgis-sdk CLI becomes a thin wire client and exit-code/error mapper; new and existing CLI commands are routed through Rust, and _fallback_cli.py plus the Python implementations of those commands are removed or reduced to a deliberate native-extension-unavailable error with no alternate command semantics.
- [ ] #4 The qgis-sdk CLI path does not import or call PyQGIS/PyQt; the package's plugin runtime/UI integrations remain explicitly separated and documented as the only QGIS-hosted boundary.
- [ ] #5 Protocol and engine integration tests cover successful commands, structured failures, transport mismatch, filesystem/side-effect boundaries, and stable stdout/stderr/exit-code behavior; Python tests exercise the real native extension and prove no fallback path is used.
- [ ] #6 Package manifests, build targets, CLI documentation, and the qgis-sdk architecture document describe the new engine/protocol ownership and the supported installation/runtime requirements.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria are checked with focused conventional commits and the task's final summary records the chosen architecture and rejected alternative.
- [ ] #2 pixi run gates passes, including Rust, Python, source-visibility, and package checks; native CLI tests run without PyQGIS imports.
- [ ] #3 No duplicated Python/Rust command implementation or silent fallback remains in the shipped qgis-sdk CLI.
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Build the canonical Rust qgis-plugin command library and exact qgis-sdk alias. Keep qgis-sdk CLI tooling separate from qgis-cli GIS execution, use shared protocol/engine components only where appropriate, and keep QGIS-hosted plugin runtime outside this CLI boundary.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The accepted product boundary is recorded in doc-7. qgis-sdk must not depend directly on qgis-py; its Rust CLI may reuse shared protocol/engine crates, while hosted UI and Processing remain PyQGIS/PyQt-owned. Follow TASK-40, TASK-43, and TASK-44 for the decomposed work.
<!-- SECTION:NOTES:END -->
