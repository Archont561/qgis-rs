---
id: TASK-25.4
title: 'RFC 19: resolve open questions and record the native-manager ADR'
status: To Do
assignee: []
created_date: '2026-10-03 02:16'
labels:
  - rfc
  - ffi
  - architecture
  - decision
dependencies: []
references:
  - 'https://github.com/Archont561/qgis-rs/issues/19'
documentation:
  - .knowledge/decisions/D09-wire-protocol-over-ffi.md
  - .knowledge/decisions/INDEX.md
parent_task_id: TASK-25
priority: high
type: spike
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Issue #19 is already represented by parent task TASK-25 and phase subtasks TASK-25.1 through TASK-25.3, but the RFC's structural open questions are currently bundled into the parent acceptance criteria. Extract that prerequisite into an explicit child task so the native-manager phases do not start with unresolved boundary decisions.

Resolve the RFC's concurrency model (one global mutex versus a dedicated QGIS thread/queue), the single source of truth for the wire schema when C++ also reads the envelope, the path-based binary-artifact policy, and whether crash isolation remains out of scope. Reconcile the issue's camelCase examples with the shipped snake_case protocol, then record the decision in a new ADR or an explicit update to the accepted protocol decision before implementation phases begin.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The concurrency model for QGIS access is selected, justified against QGIS thread-affinity requirements, and specified as an invariant for qgis_invoke.
- [ ] #2 The source of truth for the JSON envelope and operation schema shared by Rust and C++ is selected, including how transport-version and snake_case naming are enforced.
- [ ] #3 The binary-artifact policy is confirmed or changed, and crash isolation/subprocess transport is explicitly scoped in or out for RFC 19.
- [ ] #4 Issue #19's camelCase examples versus the shipped snake_case protocol are reconciled in the issue and the repository documentation.
- [ ] #5 A reviewed ADR is added or updated under .knowledge/decisions, and TASK-25.1 through TASK-25.3 can reference this decision without reopening the same questions.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 The task is linked as a child of TASK-25 and references issue #19 and D09.
- [ ] #2 No native manager implementation begins until the selected invariants are recorded.
<!-- DOD:END -->
