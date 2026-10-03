---
id: TASK-27
title: Reconcile draft knowledge decisions with current backlog and architecture
status: Done
assignee: []
created_date: '2026-10-03 02:12'
updated_date: '2026-10-03 17:28'
labels:
  - knowledge
  - backlog
  - architecture
  - documentation
milestone: m-5
dependencies: []
references:
  - .knowledge/decisions
  - .knowledge/qgis-plugin-sdk.md
  - .knowledge/qgis-plugin-ui.md
  - .knowledge/CONTEXT.md
  - .knowledge/api-design.md
  - .knowledge/architecture.md
  - .knowledge/build-system.md
  - .knowledge/qgis-vector-layer.md
  - .knowledge/scaffold.md
  - .knowledge/testing.md
  - .knowledge/release.md
  - backlog/docs/roadmap/doc-2 - QGIS-RS-Execution-Roadmap.md
documentation:
  - >-
    backlog/docs/knowledge-backlog-map/doc-1 -
    Knowledge-to-backlog-migration-map.md
  - .knowledge/INDEX.md
  - backlog/docs/roadmap/doc-2 - QGIS-RS-Execution-Roadmap.md
  - .knowledge/architecture.md
  - .knowledge/api-design.md
  - .knowledge/build-system.md
  - .knowledge/qgis-plugin-sdk.md
  - .knowledge/qgis-plugin-ui.md
  - .knowledge/qgis-vector-layer.md
  - .knowledge/scaffold.md
  - .knowledge/testing.md
  - .knowledge/release.md
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
- [x] #1 Every actionable section in the Backlog execution roadmap, api-design.md, qgis-plugin-sdk.md, qgis-plugin-ui.md, qgis-vector-layer.md, scaffold.md, testing.md, release.md, and the decision records is classified as an existing task, a new task, durable knowledge, or obsolete; the classification is recorded in the migration map.
- [x] #2 Draft decisions D01-D08 are compared with the current crates and accepted decisions D09-D11; each is marked accepted, superseded, rejected, or still open with rationale and links to the relevant backlog tasks.
- [x] #3 Existing tasks are updated or linked rather than duplicated, and any genuinely missing implementation job extracted from the knowledge base has acceptance criteria, source documentation, dependencies, and an appropriate priority/type.
- [x] #4 Knowledge documents retain durable context, design rationale, and operational instructions; implementation status and next actions point to backlog task IDs so status is not maintained in two places.
- [x] #5 The knowledge index, Backlog execution roadmap, milestones, and migration map contain working links to backlog tasks/docs/decisions and the resulting map can be used by a future session to select ready work.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All migration changes use the backlog CLI for task/doc metadata and are committed in one focused conventional commit.
- [x] #2 pixi run backlog task list --ready --plain and the relevant documentation/link checks pass.
- [x] #3 Durable knowledge remains in .knowledge/ with working links; the executable roadmap is intentionally moved to backlog/docs/roadmap and no source link is broken.
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Audit every knowledge entry and decision against the current crates and backlog, preserving durable rationale and runbook content.
2. Move executable planning from the knowledge bundle into Backlog.md documentation and milestones.
3. Update the knowledge index and existing task documentation without duplicating work or retaining a second roadmap.
4. Validate links and backlog readiness, then close the task with evidence.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started the knowledge-to-backlog reconciliation. No GitHub workflows were running; the working tree was clean at 12fdcc2.

Expanded the migration map with section-level classifications for every required knowledge document and explicit D01–D12 dispositions.

Updated architecture, build, testing, SDK/UI, vector-layer, scaffold, release, index, and CONTEXT pointers so implementation status and next actions resolve to backlog tasks.

Validated 0 missing relative links across the knowledge and migration-map Markdown files and verified the ready queue with the Backlog.md CLI. The repository Pixi environment is absent, so the exact pixi-run gate remains unproven.

Migration pass completed: populated documentation fields on existing task owners for the API, SDK/UI, bindings, testing, release, and RFC 19 sections, preserving all pre-existing task documentation links.

No new task was created because the audit found no uncovered executable work; open D02/D04/D06/D08 outcomes already map to TASK-8/TASK-10, TASK-5–TASK-12, TASK-9/TASK-25.2, and TASK-12/TASK-25.3.

Moved executable roadmap planning from the knowledge bundle into Backlog.md milestones m-0 through m-5 and the Backlog document doc-2.

Roadmap migration completed: removed the former knowledge roadmap, created Backlog document doc-2, created milestones m-0 through m-5, and assigned all current tasks to a milestone.

2026-10-03: Re-ran pixi run backlog task list --ready --plain after restoring the environment; the ready queue completed successfully and no dependency metadata errors were reported.

2026-10-03: Checked 131 relative Markdown links across .knowledge (excluding the historical session log) and the knowledge-backlog migration map; 0 missing targets.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The knowledge-to-backlog reconciliation is complete. Acceptance criteria remain checked, the ready queue is proven with the restored Pixi/Bun environment, and all links in the maintained knowledge and migration-map documents resolve.
<!-- SECTION:FINAL_SUMMARY:END -->
