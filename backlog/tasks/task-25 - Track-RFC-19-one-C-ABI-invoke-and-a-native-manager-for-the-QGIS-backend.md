---
id: TASK-25
title: 'Track RFC 19: one C-ABI invoke and a native manager for the QGIS backend'
status: Done
assignee: []
created_date: '2026-10-02 23:23'
updated_date: '2026-10-03 22:11'
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
- [x] #1 The RFC's open questions are answered in writing: one global mutex or a dedicated QGIS thread, where qgis-protocol lives once C++ also reads the envelope, whether path-based binary artifacts stay the policy, and whether subprocess crash isolation stays out of scope
- [x] #2 The decision is recorded as an ADR in .knowledge/decisions and the issue is updated with the outcome
- [x] #3 The snake_case versus camelCase discrepancy between the RFC text and the shipped wire is resolved in the issue, not only in the code
- [x] #4 Phases 2, 3 and 4 of the migration sketch are tracked as subtasks and closed in order
- [x] #5 The issue is closed only when no cxx or cxx-build dependency remains in crates/qgis-sys
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-04: closed on the state of the tree, checked fact by fact rather than inherited from the subtasks.

AC#1/#2: the four open questions are answered in D12 — one dedicated QGIS owner thread with a blocking queue (section 1), qgis-protocol as the normative contract once C++ also reads the envelope (section 2), path-based artifacts with metadata in the response (section 3), and crash isolation deferred to a later out-of-process transport (section 4). Issue 19 carries the resolution comment pointing at TASK-25.4 and D12 and is CLOSED.

AC#3: the naming discrepancy is resolved in writing, not only in code — D12 section 5 is the amendment (the RFC text says transportVersion, the shipped wire is snake_case everywhere including operation names), and the issue comment carries it. The protocol crate documentation says the same thing in the place a client reads.

AC#4: the phases are closed in order — 25.1 Done, 25.2 Done, 25.3 Done this session once the restored sandbox could run the QGIS-backed suites. 25.3 was the last open one and was In Progress only because its proof needed QGIS.

AC#5: verified by inspection, not memory — grep finds no cxx or cxx-build anywhere in crates/qgis-sys (manifest, build.rs or sources); the crate is one C-ABI adapter plus one C++ translation unit. The one survival is in the scaffolder: xtask scaffold still generates a cxx::bridge module and a rust/cxx.h include for a crate that no longer has cxx, so the next binding scaffolded from it would reintroduce the dependency the RFC removed. That is a generator bug, not a qgis-sys dependency, so AC#5 stands — recorded here and in .knowledge/log.md so it becomes its own task.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
RFC 19 is complete. One C-ABI invoke plus a native manager replaced the cxx bridge: qgis-sys carries no cxx or cxx-build, the thirteen operations answer through the JSON envelope, the open questions are answered in D12 (owner thread, normative qgis-protocol, path-based artifacts, deferred crash isolation) with the snake_case amendment recorded in the issue, and phases 2, 3 and 4 closed in order — phase 4 last, once a restored QGIS environment could prove render_map and export_features against real QGIS. Follow-up noted: xtask scaffold still emits cxx bridges and would reintroduce the dependency for the next binding.
<!-- SECTION:FINAL_SUMMARY:END -->
