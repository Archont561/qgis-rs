---
id: TASK-27
title: Reconcile draft knowledge decisions with current backlog and architecture
status: To Do
assignee: []
created_date: '2026-10-03 02:12'
labels:
  - knowledge
  - backlog
  - architecture
  - documentation
dependencies: []
references:
  - .knowledge/decisions
  - .knowledge/qgis-plugin-sdk.md
  - .knowledge/qgis-plugin-ui.md
documentation:
  - >-
    backlog/docs/knowledge-backlog-map/doc-1 -
    Knowledge-to-backlog-migration-map.md
  - .knowledge/INDEX.md
  - .knowledge/ROADMAP.md
priority: medium
type: docs
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Audit the OKF knowledge bundle and make its actionable work visible in Backlog.md without destroying the durable architecture and runbook knowledge.

The repository already has backlog tasks covering most roadmap/API work, but several knowledge documents still carry draft decision states, implementation-status tables, future-work lists, and stale descriptions. Reconcile those entries against the current crates and the existing backlog, create only genuinely missing jobs, and keep `.knowledge/` as the canonical home for context, rationale, and accepted decisions. Use `backlog/docs/knowledge-backlog-map/doc-1 - Knowledge-to-backlog-migration-map.md` as the traceability index.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every actionable section in ROADMAP.md, api-design.md, qgis-plugin-sdk.md, qgis-plugin-ui.md, qgis-vector-layer.md, scaffold.md, testing.md, release.md, and the decision records is classified as an existing task, a new task, durable knowledge, or obsolete; the classification is recorded in the migration map.
- [ ] #2 Draft decisions D01-D08 are compared with the current crates and accepted decisions D09-D11; each is marked accepted, superseded, rejected, or still open with rationale and links to the relevant backlog tasks.
- [ ] #3 Existing tasks are updated or linked rather than duplicated, and any genuinely missing implementation job extracted from the knowledge base has acceptance criteria, source documentation, dependencies, and an appropriate priority/type.
- [ ] #4 Knowledge documents retain durable context, design rationale, and operational instructions; implementation status and next actions point to backlog task IDs so status is not maintained in two places.
- [ ] #5 The knowledge index, roadmap, and migration map contain working links to the backlog tasks/docs/decisions and the resulting map can be used by a future session to select ready work.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All migration changes use the backlog CLI for task/doc metadata and are committed in one focused conventional commit.
- [ ] #2 No knowledge document is deleted or moved in a way that breaks existing source links; obsolete material is explicitly marked or archived with a reason.
- [ ] #3 pixi run backlog task list --ready --plain and the relevant documentation/link checks pass.
<!-- DOD:END -->
