---
id: TASK-25
title: 'Track RFC 19: one C-ABI invoke and a native manager for the QGIS backend'
status: To Do
assignee: []
created_date: '2026-10-02 23:23'
updated_date: '2026-10-03 08:57'
labels:
  - rfc
  - ffi
  - cpp
  - architecture
milestone: m-0
dependencies: []
references:
  - 'https://github.com/Archont561/qgis-rs/issues/19'
documentation:
  - .knowledge/architecture.md
  - .knowledge/decisions/D09-wire-protocol-over-ffi.md
  - .knowledge/decisions/D12-qgis-native-manager-over-c-abi.md
  - .knowledge/decisions/INDEX.md
  - >-
    backlog/docs/architecture/doc-4 -
    QGIS-Native-Manager-and-API-Coverage-Strategy.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Tracking task for the open RFC in the repository, issue 19: replace the cxx bridge with one C-ABI entry point into a native manager, and keep the JSON envelope that already crosses the Python and Node boundaries as the wire between Rust and C++ as well.

The RFC's shape: three C exports (qgis_invoke(const char*) -> char*, qgis_free(char*), qgis_transport_version(void) -> unsigned), one C++ manager translation unit as the only file that includes qgs*.h, QJsonDocument for parsing and writing so no new dependency appears, an ID registry for live QGIS objects instead of pointers crossing the boundary, a try/catch fence before every extern "C" return, and -fvisibility=hidden so only those three symbols are exported. On the Rust side that is roughly thirty lines of extern "C" and no cxx, cxx-build or bindgen; qgis-render stays pure Rust behind a small router that forwards only the operations that need QGIS.

State of play after PR 20: phase 1 of the RFC's migration sketch is already shipped. The protocol crate, the router, the envelope and the single-function bindings exist, the thirteen operations are live, and both language clients call one invoke. The one difference from the RFC text is naming: the RFC writes transportVersion in camelCase, while the shipped wire is snake_case everywhere, including operation names, and the three clients and their golden tests agree on that. The RFC should be read with snake_case substituted, or amended.

What is left is phases 2 to 4, tracked as the subtasks of this task. Before the first of them starts, the RFC's own open questions need answers, because they are structural rather than incremental.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The RFC's open questions are answered in writing: one global mutex or a dedicated QGIS thread, where qgis-protocol lives once C++ also reads the envelope, whether path-based binary artifacts stay the policy, and whether subprocess crash isolation stays out of scope
- [ ] #2 The decision is recorded as an ADR in .knowledge/decisions and the issue is updated with the outcome
- [ ] #3 The snake_case versus camelCase discrepancy between the RFC text and the shipped wire is resolved in the issue, not only in the code
- [ ] #4 Phases 2, 3 and 4 of the migration sketch are tracked as subtasks and closed in order
- [ ] #5 The issue is closed only when no cxx or cxx-build dependency remains in crates/qgis-sys
<!-- AC:END -->
