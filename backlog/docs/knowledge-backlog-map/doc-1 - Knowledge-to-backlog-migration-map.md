---
id: doc-1
title: Knowledge-to-backlog migration map
type: guide
created_date: '2026-10-03 02:12'
---

# Knowledge-to-backlog migration map

This map records the first-pass classification of the `.knowledge/` bundle. It is deliberately
non-destructive: `.knowledge/` remains the source of durable context, design rationale, accepted
decisions, and runbooks; `backlog/` is the source of executable work, acceptance criteria,
dependencies, and status.

The audit and any future extraction work are tracked by [TASK-27](../../tasks/task-27%20-%20Reconcile-draft-knowledge-decisions-with-current-backlog-and-architecture.md).

## Classification rules

- **Keep as knowledge** — stable context, rationale, API/design specification, how-to material,
  or historical log material.
- **Track as backlog work** — implementation, migration, validation, documentation, or an open
  decision that has a testable outcome.
- **Link, do not duplicate** — if a task already exists, add the knowledge source with `--doc` or
  `--ref`; do not create a second task for the same work.
- **External follow-up** — an issue belongs in another repository. For example, the published
  `pixi-sandbox` consumer-restore failure is tracked upstream as
  [pixi-sandbox#81](https://github.com/Archont561/pixi-sandbox/issues/81), not as a duplicate qgis-rs
  implementation task.

## File classification

| Knowledge entry | Classification | Backlog destination or existing work |
|---|---|---|
| `CONTEXT.md` | Keep as agent/contributor orientation | References the repository invariants and current crate layout. |
| `INDEX.md` | Keep as the knowledge index | Add task/doc links when the migration audit lands. |
| `ROADMAP.md` | Keep as strategy; extract milestones | Data-access and wrapper work is represented by TASK-5 through TASK-12; status reconciliation is TASK-27. |
| `api-design.md` | Keep as API specification | OGC/server coverage is TASK-19; wire-protocol documentation is TASK-20; QGIS backend RFC work is TASK-25 and TASK-25.1–TASK-25.3. |
| `architecture.md` | Keep as architecture reference | Reconcile stale/future crate claims under TASK-27. |
| `build-system.md` | Keep as build runbook | Toolchain dependency work is TASK-24; no separate task for explanatory material. |
| `documentation-site.md` | Keep as docs deployment runbook | Public protocol documentation is TASK-20; general site operation remains knowledge. |
| `env-provisioning.md` | Keep as environment runbook | The current restore defect is external: pixi-sandbox#81. |
| `ffishim.md` | Keep as FFI how-to | Binding implementation is TASK-5 through TASK-12 and TASK-25.x. |
| `lefthook.md` | Keep as contributor runbook | No untracked implementation job identified. |
| `log.md` | Keep as immutable-ish history | Do not turn historical entries into tasks; extract only genuinely open items. |
| `pixi.md` | Keep as environment/task reference | Release and automation validation is TASK-21; toolchain work is TASK-24. |
| `qgis-application.md` | Keep as lifecycle design/runbook | Application/wrapper implementation is covered by TASK-8 and the RFC-19 tasks. |
| `qgis-plugin-sdk.md` | Keep as SDK product specification | TASK-3, TASK-4, TASK-13 through TASK-18, and TASK-26 cover its open implementation/documentation areas. |
| `qgis-plugin-ui.md` | Keep as UI specification/status reference | Web and framework scaffolding is TASK-18; status reconciliation belongs to TASK-27. |
| `qgis-vector-layer.md` | Keep as binding reference | Fields/features/geometry/iterator follow TASK-5 through TASK-7; future renderer work is not automatically scheduled. |
| `related-approaches.md` | Keep as research/context | No executable job without a new decision or measured spike. |
| `release.md` | Keep as release runbook | End-to-end release validation is TASK-21. |
| `scaffold.md` | Keep as contributor how-to | Scaffold/API documentation is TASK-3; packaging CLI work is TASK-17. |
| `testing.md` | Keep as testing policy/runbook | QGIS SDK CI is task-1/task-2; property and fixture migration is TASK-23. |

## Decision records

| Decision | Current handling |
|---|---|
| D01–D06 | Draft architectural assumptions referenced by TASK-5 through TASK-12. TASK-27 must compare them with the current crates and mark them accepted, superseded, rejected, or still open. |
| D07 | Draft Rust-plugin/PyO3 direction; implementation intent is represented by TASK-16. The decision itself needs reconciliation with the current wire-protocol architecture under TASK-27. |
| D08 | Draft standalone QGIS-rendering direction; rendering work is represented by TASK-12 and TASK-25.3. Reconcile its remaining open questions under TASK-27. |
| D09 | Accepted wire-protocol decision; protocol documentation is TASK-20 and the qgis-sdk CLI extension is TASK-26. |
| D10 | Accepted xtask decision; release-pipeline proof is TASK-21. |
| D11 | Accepted test-layout decision; property/fixture migration is TASK-23. |

## Backlog operating rule

When work is discovered in a knowledge document:

1. Search first: `pixi run backlog search "<term>" --plain`.
2. Reuse an existing task when the outcome matches; add the source with `task edit --add-ref` or
   `--doc`.
3. Create a draft for an idea whose scope or architecture is not settled.
4. Promote it to a task only after adding acceptance criteria, dependencies, priority, and source
   links.
5. Update the knowledge document only for rationale, constraints, or a link to the task; do not
   maintain a second status checklist there.
6. Close criteria with `--check-ac`, record evidence in notes/final summary, and complete the task
   through the backlog CLI.

This keeps the knowledge bundle useful to agents while making actionable work discoverable through
`task list --ready` and the Kanban board.
