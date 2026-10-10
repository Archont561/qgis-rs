---
id: doc-1
title: Knowledge-to-backlog migration map
type: guide
created_date: '2026-10-03 02:12'
---

# Knowledge-to-backlog migration map

This map records the reconciliation of the `.knowledge/` bundle against the
current crates, packages, and Backlog.md tasks. It is deliberately
non-destructive: `.knowledge/` remains the source of durable context, design
rationale, accepted decisions, and runbooks; `backlog/` is the source of
executable work, acceptance criteria, dependencies, and status.

The audit is tracked by [TASK-27](../../tasks/task-27%20-%20Reconcile-draft-knowledge-decisions-with-current-backlog-and-architecture.md).
The map is a traceability index, not a second Kanban board.

## Audit rules and evidence

- **Keep as knowledge** — stable context, rationale, API/design specification,
  or operational instructions.
- **Track as backlog work** — implementation, migration, validation,
  documentation, or an open decision with a testable outcome.
- **Link, do not duplicate** — if a task already exists, link the knowledge
  source with Backlog.md `--doc`/`--ref`; do not create a second task.
- **Mark historical material** — old estimates and generated status tables are
  retained when useful, but current execution status points to task IDs.
- **External follow-up** — work belonging to another repository stays external;
  for example, the consumer-restore defect is
  [pixi-sandbox#81](https://github.com/Archont561/pixi-sandbox/issues/81).

The audit compared the named knowledge files with the workspace crates under
`crates/`, the Python/TypeScript packages, the task files under `backlog/tasks/`,
and the accepted decisions D09–D12. No code or durable knowledge entry was
deleted; the executable roadmap was intentionally relocated from `.knowledge/`
into `backlog/docs/roadmap/` and its planning content was mapped to milestones.

## Section-level actionable classification

| Knowledge entry and actionable sections | Classification | Backlog destination / disposition |
|---|---|---|
| `backlog/docs/roadmap/doc-2 - QGIS-RS-Execution-Roadmap.md`: Phase 0 decisions and the Phase 1–3 binding sequence | Backlog-owned execution plan plus durable strategy links | D01–D08 dispositions below; TASK-5–TASK-12, TASK-19, TASK-20, TASK-24, TASK-25.x |
| `api-design.md`: qgis-render project/layer/feature/geometry/CRS/render API | Existing specification; implementation is split by capability | TASK-5–TASK-12 and TASK-25.3; the document now states that it is not a status ledger |
| `api-design.md`: CLI commands and protocol-facing operations | Existing specification and documentation gap | TASK-17, TASK-20, TASK-21, TASK-26; implemented pure-Rust behavior remains in crate tests |
| `api-design.md`: HTTP WMS/WFS/OGC API surface | Existing specification with integration work | TASK-19; no duplicate task created |
| `qgis-sdk.md`: plugin, algorithm, network, task, wrapper, packaging, and Rust-acceleration sections | Existing SDK specification and implementation evidence | TASK-1–TASK-4, TASK-3, TASK-13–TASK-18, TASK-26; status table now points to owners |
| `qgis-ui.md`: Qt Designer, WebEngine, QWebChannel, framework templates, testing | Existing UI specification and evidence | TASK-1–TASK-4, TASK-3, TASK-18; status is explicitly owned by Backlog.md |
| `qgis-vector-layer.md`: current bindings and future fields/features/geometry/editing | Durable binding reference plus existing work | TASK-5–TASK-7, TASK-11, TASK-25.2; future list now links task IDs |
| `scaffold.md`: scaffold usage, generated files, and post-scaffold steps | Durable contributor how-to | TASK-3 and TASK-5–TASK-7; no new job |
| `testing.md`: QGIS environment, fixtures, single-threading, test commands | Durable testing runbook with stale command names corrected | TASK-1, TASK-2, TASK-4, TASK-23; repository gates are D10/`pixi run gates` |
| `release.md`: release model, registries, credentials, and workflow | Durable release runbook | TASK-21 owns executable release proof; no duplicate task |
| `architecture.md`: crate model and CXX data flow | Durable architecture, corrected to current workspace | D09/D12 and TASK-24/TASK-25.x; no `crates/qgis` claim remains as current state |
| `build-system.md`: qgis-sys build.rs, CXX/cc, paths, compile commands | Durable build runbook, extended with toolchain ownership split | TASK-24 owns CMake/Ninja/GTest/RapidCheck prerequisites |
| `CONTEXT.md` and `INDEX.md`: orientation and navigation | Durable agent/contributor context | Links now point to the migration map, D12, and task-owned execution |
| `env-provisioning.md`, `pixi.md`: environment and restore behavior | Durable environment runbooks | External consumer-restore issue is pixi-sandbox#81; local toolchain work is TASK-24 |
| `ffishim.md`, `qgis-application.md`: binding/lifecycle how-to | Durable technical reference | TASK-5–TASK-12 and TASK-25.1–TASK-25.3 |
| `documentation-site.md`: Astro/Starlight operation | Durable docs runbook | TASK-20 owns protocol publication; general site operation stays knowledge |
| `lefthook.md`: contributor hooks | Durable contributor runbook | D10/xtask; no untracked job identified |
| `log.md`: historical entries | Immutable-ish history | No migration; only genuinely open items may become tasks |
| `related-approaches.md`: research and alternatives | Durable research context | No executable job without a new decision or measured spike |

## Required-document section index

Adjacent sections with the same owner are grouped below; every actionable
section named by TASK-27 has a classification and an owner. Examples and
rationale remain in the source documents.

| Source sections | Classification | Owner |
|---|---|---|
| `backlog/docs/roadmap/doc-2 - QGIS-RS-Execution-Roadmap.md` Phase 0 / decision log | Backlog-owned execution plan and decision links | TASK-27 and D01–D12 |
| `backlog/docs/roadmap/doc-2 - QGIS-RS-Execution-Roadmap.md` Phase 1 data access | Existing implementation work | TASK-5, TASK-6, TASK-7 |
| `backlog/docs/roadmap/doc-2 - QGIS-RS-Execution-Roadmap.md` Phase 2 project/editing | Existing implementation work | TASK-10, TASK-11 |
| `backlog/docs/roadmap/doc-2 - QGIS-RS-Execution-Roadmap.md` Phase 3 rendering | Existing implementation work | TASK-12, TASK-19, TASK-25.3 |
| `api-design.md` 1.1–1.6 core project/layer/features/geometry/CRS | Target API plus existing pure-Rust subset | TASK-5–TASK-11 |
| `api-design.md` 1.7–1.10 rendering/tiles/expressions/layouts | Target API and backend work | TASK-12, TASK-14, TASK-25.3 |
| `api-design.md` 1.11–1.12 errors/server mode | Existing design plus integration work | TASK-9, TASK-19 |
| `api-design.md` 2.1–2.8 CLI commands | Target CLI contract and documentation | TASK-17, TASK-20, TASK-21, TASK-26 |
| `api-design.md` 3.1–3.3 HTTP/OGC server | Target server contract | TASK-19 |
| `api-design.md` 4–5 Python/Node bindings | D09 host-language boundary and target ergonomic APIs | TASK-20, TASK-26; no duplicate binding task |
| `api-design.md` 6 type reference / 7 design principles | Durable specification | Keep as knowledge |
| `qgis-sdk.md` sections 1–4 plugin, processing, wrappers, plugin types | SDK specification and implementation work | TASK-3, TASK-4, TASK-13–TASK-16 |
| `qgis-sdk.md` sections 5–6 CLI/configuration | Existing CLI and packaging work | TASK-3, TASK-17, TASK-26 |
| `qgis-sdk.md` sections 7–8 testing/unified backend | Runtime proof and backend boundary | TASK-1, TASK-2, TASK-4, TASK-13–TASK-16, TASK-23 |
| `qgis-sdk.md` sections 9–11 product structure/effort/alternatives | Durable product context; old estimates are historical | Keep as knowledge; no status task |
| `qgis-sdk.md` section 12 implementation evidence | Evidence snapshot, not status | TASK-1–TASK-4, TASK-13–TASK-18, TASK-26 |
| `qgis-ui.md` sections 1–3 Qt/WebEngine/declarative modules | UI specification and implementation evidence | TASK-3, TASK-18 |
| `qgis-ui.md` sections 4–5 templates/testing | Scaffold and runtime test work | TASK-3, TASK-1, TASK-2, TASK-4 |
| `qgis-ui.md` sections 6–7 references/status/typed bridge | Durable reference plus package follow-up | TASK-18; status in Backlog.md |
| `qgis-vector-layer.md` overview/current bindings/provider/fixture | Durable binding reference | Keep as knowledge |
| `qgis-vector-layer.md` Future Additions | Existing actionable binding work | TASK-5–TASK-7, TASK-11, TASK-12, TASK-14, TASK-25.2 |
| `scaffold.md` usage/generated files/wiring | Durable how-to | TASK-3; concrete bindings TASK-5–TASK-7 |
| `scaffold.md` post-scaffold steps | Contributor procedure | D10 and TASK-3; no separate task |
| `testing.md` test types/environment/threading/fixtures | Durable runbook | TASK-1, TASK-2, TASK-4, TASK-23 |
| `testing.md` old `test`/`test-full` commands | Obsolete command names | Corrected to D10/`pixi run gates` and direct cargo test commands |
| `release.md` release halves/version/builds/credentials | Durable runbook | TASK-21 owns executable proof |
| `release.md` workflow/release validation gaps | Existing validation work | TASK-21 |
| Decision records D01–D12 | Decision dispositions | Table below |

## Decision record dispositions

This table is the authoritative first-pass reconciliation of D01–D12. A
record may remain in `.knowledge/` with `status: draft` when its rationale is
still useful; the disposition below says whether it governs current work.

| Decision | Disposition | Current reading and backlog links |
|---|---|---|
| [D01 — Two-Crate Architecture](../../../.knowledge/decisions/D01-two-crate-architecture.md) | **Superseded** | The current workspace is `qgis-sys` + `qgis-render`/`qgis-engine` plus bindings; there is no `crates/qgis` safe-wrapper crate. Reconcile the historical wrapper work through TASK-8 and TASK-27. |
| [D02 — Ownership Model](../../../.knowledge/decisions/D02-ownership-model.md) | **Still open** | The owned/transferred/borrowed rationale remains useful for future wrappers (TASK-8/TASK-10), while RFC 19 uses manager-owned integer IDs (TASK-25.1, D12). |
| [D03 — Error Handling](../../../.knowledge/decisions/D03-error-handling.md) | **Superseded** at the transport boundary | D09/D12 use structured JSON error envelopes; legacy qgis-sys error accessors and safe-wrapper mapping remain implementation work in TASK-9 and TASK-25.1. |
| [D04 — API Binding Priority](../../../.knowledge/decisions/D04-api-priority.md) | **Still open** as a planning principle | Its tiers map to TASK-5–TASK-12; it is not an accepted ABI or ownership contract. |
| [D05 — Threading Model](../../../.knowledge/decisions/D05-threading.md) | **Superseded/qualified** by D12 | QGIS remains single-owner and QGIS objects stay off worker threads; RFC 19 exposes a blocking owner queue. TASK-25.1 implements the D12 invariant. |
| [D06 — String Strategy](../../../.knowledge/decisions/D06-string-strategy.md) | **Still open** as a performance policy | Boundary conversion remains the default; batch extraction is required for layer features in TASK-25.2 and string/error work is TASK-9. |
| [D07 — Rust QGIS Plugins via PyO3](../../../.knowledge/decisions/D07-rust-qgis-plugins.md) | **Superseded** as the whole-product direction | The current SDK and engine have separate host/runtime boundaries; Rust acceleration remains TASK-16 and the native CLI architecture is TASK-26. |
| [D08 — Standalone Rendering App](../../../.knowledge/decisions/D08-standalone-rendering-app.md) | **Still open** as a product/implementation direction | `qgis-render` and CLI scaffolding exist, but the QGIS backend is not live. Rendering work is TASK-12 and TASK-25.3. |
| [D09 — Wire Protocol over FFI](../../../.knowledge/decisions/D09-wire-protocol-over-ffi.md) | **Accepted** | Normative one-invoke JSON boundary for qgis-py/qgis-node; protocol documentation is TASK-20, native-manager extension is D12/TASK-25. |
| [D10 — xtask over Shell Scripts](../../../.knowledge/decisions/D10-xtask-over-shell-scripts.md) | **Accepted** | Repository automation is `pixi run xtask`; gate and release proof are TASK-21 and the D10 commands. |
| [D11 — Tests Outside `src/`](../../../.knowledge/decisions/D11-tests-outside-src.md) | **Accepted** | Source/tests layout is current repository policy; property/fixture migration is TASK-23. |
| [D12 — QGIS Native Manager over C ABI](../../../.knowledge/decisions/D12-qgis-native-manager-over-c-abi.md) | **Accepted** | Current RFC 19 gate: owner queue, normative protocol, path artifacts, deferred crash isolation. TASK-25.1–TASK-25.3 depend on it. |
| [D13 — Rust CLI, FFI, and QGIS SDK product boundaries](../../../.knowledge/decisions/D13-rust-cli-ffi-and-qgis-sdk-boundaries.md) | **Accepted** | Product boundaries for qgis-cli / qgis_rs / qgis_sdk; CLI launcher stabilization is TASK-42; the ui preview dev loop is doc-10 / TASK-54. |
| [D14 — qgis-sdk CLI transport](../../../.knowledge/decisions/D14-qgis-sdk-cli-transport-argv-forwarding.md) | **Accepted** | CLI transport is native argv forwarding (`cli_main` pyfunction; Python parses nothing); capabilities stay on the D09 wire protocol; a missing native extension is a loud CLI error. Implementation is TASK-26 / TASK-41 / TASK-42. |

## Existing-task reconciliation

No new implementation task was created: every actionable item found in the
named knowledge entries already has a matching backlog owner or is explicitly
durable context. The following existing records were reconciled during this
audit:

- TASK-24 is now `In Progress`: source evidence confirms the Pixi declarations
  and lock entries; environment restoration and provenance remain unchecked.
- TASK-25.1 depends on both TASK-25.4 and TASK-24, so the native manager cannot
  start before its ADR and C++ toolchain prerequisites.
- TASK-25.4 owns D12 and its RFC 19 decision gate.
- TASK-26 owns the unresolved qgis-sdk CLI engine/protocol choice rather than
  duplicating it in the knowledge bundle.
- TASK-1 remains the owner of SDK headless/runtime proof; knowledge tables no
  longer claim that their snapshots are the current status source.
- The migration pass populated the `documentation:` fields of every existing
  task owner referenced by the matrix, including TASK-5–TASK-12, TASK-13–TASK-21,
  TASK-23–TASK-26, while preserving their pre-existing decision and architecture
  links. This is the executable traceability migration; durable knowledge stays
  in `.knowledge/`, while the roadmap was intentionally moved to
  `backlog/docs/roadmap/`.

## Backlog operating rule

When work is discovered in a knowledge document:

1. Search first: `pixi run backlog search "<term>" --plain`.
2. Reuse an existing task when the outcome matches; add the source with
   `task edit --add-ref` or `--doc`.
3. Create a draft for an idea whose scope or architecture is not settled.
4. Promote it only after acceptance criteria, dependencies, priority, type, and
   source links are present.
5. Update knowledge only for rationale, constraints, durable examples, or a
   link to the task; do not maintain a second status checklist.
6. Close criteria with `--check-ac`, record evidence in notes/final summary,
   and complete the task through the backlog CLI.

This keeps the knowledge bundle useful to agents while making actionable work
discoverable through `task list --ready --plain` and the Kanban board.
