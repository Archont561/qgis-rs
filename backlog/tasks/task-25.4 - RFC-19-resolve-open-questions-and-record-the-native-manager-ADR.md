---
id: TASK-25.4
title: 'RFC 19: resolve open questions and record the native-manager ADR'
status: In Progress
assignee: []
created_date: '2026-10-03 02:16'
updated_date: '2026-10-03 17:45'
labels:
  - rfc
  - ffi
  - architecture
  - decision
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
- [x] #1 The concurrency model for QGIS access is selected, justified against QGIS thread-affinity requirements, and specified as an invariant for qgis_invoke.
- [x] #2 The source of truth for the JSON envelope and operation schema shared by Rust and C++ is selected, including how transport-version and snake_case naming are enforced.
- [x] #3 The binary-artifact policy is confirmed or changed, and crash isolation/subprocess transport is explicitly scoped in or out for RFC 19.
- [ ] #4 Issue #19's camelCase examples versus the shipped snake_case protocol are reconciled in the issue and the repository documentation.
- [x] #5 A reviewed ADR is added or updated under .knowledge/decisions, and TASK-25.1 through TASK-25.3 can reference this decision without reopening the same questions.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 The task is linked as a child of TASK-25 and references issue #19 and D09.
- [x] #2 No native manager implementation begins until the selected invariants are recorded.
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Read D05, D09, the shipped qgis-protocol/qgis-engine boundary, qgis-sys QGIS lifecycle, and issue #19.
2. Record the native-manager concurrency, schema, artifact, crash-isolation, and naming decisions in D12.
3. Update decision indexes, RFC phase references, and issue #19.
4. Verify the decision links and repository checks, then close this task with evidence.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started the architecture spike. Workflow check: no GitHub runs are active for arena/01a0ff70-qgis-rs. The checkout is synchronized with origin at 9ad8ed4.

Added D12 and linked it from D09, the decision indexes, the parent RFC tracker, and phases 2–4.

Posted the resolution text to backlog/drafts/issue-19-status-comment.md because gh issue comment 19 was denied with Resource not accessible by integration; AC #4 remains unchecked until issue #19 is updated.

2026-10-03: Repository-side reconciliation is present in D12, including the dedicated QGIS owner thread, normative qgis-protocol contract, path-based artifacts, deferred crash isolation, and the snake_case amendment for the RFC examples.

2026-10-03: Re-read issue #19; it remains open and still contains the original camelCase examples. A direct gh API comment attempt returned HTTP 403 Resource not accessible by integration, so AC #4 remains unchecked. The ready-to-post resolution is retained in backlog/drafts/issue-19-status-comment.md.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Arena Agent
created: 2026-10-03 17:45
---
Prepared the issue #19 comment body with a direct [TASK-25.4 link](https://github.com/Archont561/qgis-rs/blob/arena/01a102bb-qgis-rs/backlog/tasks/task-25.4%20-%20RFC-19-resolve-open-questions-and-record-the-native-manager-ADR.md). The ready-to-paste body is retained in [backlog/drafts/issue-19-status-comment.md](https://github.com/Archont561/qgis-rs/blob/arena/01a102bb-qgis-rs/backlog/drafts/issue-19-status-comment.md); AC #4 remains unchecked until the external issue is updated.
---
<!-- COMMENTS:END -->
