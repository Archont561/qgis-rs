---
id: doc-2
title: QGIS-RS Execution Roadmap
type: guide
created_date: '2026-10-03 08:30'
updated_date: '2026-10-03 08:32'
---
# Roadmap

This document is the executable planning view for qgis-rs. Backlog.md is the
source of truth for status, acceptance criteria, dependencies, milestones, and
execution order. Durable architecture, rationale, decisions, and runbooks
remain in `.knowledge/`; the knowledge-to-backlog traceability map is
[doc-1](../knowledge-backlog-map/doc-1%20-%20Knowledge-to-backlog-migration-map.md).

## Milestones

The execution plan is represented by Backlog.md milestones, not by a status
list in the knowledge bundle:

| Milestone | Scope | Tasks |
|---|---|---|
| `m-0` — Architecture and Native Manager Foundation | D09–D12, C++ toolchain, RFC 19 manager foundation | TASK-24, TASK-25, TASK-25.1, TASK-25.4 |
| `m-1` — QGIS Bindings and Data Access | qgis-sys bindings, safe-wrapper foundations, errors, and data access | TASK-5–TASK-9 |
| `m-2` — Project, Editing, and Rendering | Project/editing bindings, rendering, server integration, and RFC 19 operations | TASK-10–TASK-12, TASK-19, TASK-25.2, TASK-25.3 |
| `m-3` — Plugin SDK and Tooling | SDK tests, APIs, wrappers, acceleration, packaging, UI, and CLI | TASK-1–TASK-4, TASK-13–TASK-18, TASK-26 |
| `m-4` — Quality, Protocol, and Release | Protocol docs, testing migration, benchmarks, and release proof | TASK-20–TASK-23 |
| `m-5` — Knowledge and Backlog Migration | Move executable planning into Backlog.md and retain durable knowledge | TASK-27 |

Use `backlog milestone list --plain` for milestone progress and
`backlog task list --plain` for current task status.

## Current execution order

The highest-impact architectural path is:

1. [TASK-25.4](../../tasks/task-25.4%20-%20RFC-19-resolve-open-questions-and-record-the-native-manager-ADR.md) — resolve the RFC 19 manager invariants and ADR.
2. [TASK-24](../../tasks/task-24%20-%20Add-cmake-and-ninja-to-the-C-toolchain-dependencies.md) — provide the C++ toolchain prerequisites; it may run in parallel with TASK-25.4.
3. [TASK-25.1](../../tasks/task-25.1%20-%20RFC-19-phase-2-native-manager-ID-registry-and-lifecycle-behind-qgis_invoke.md) — implement the native manager only after both prerequisites.
4. [TASK-25.2](../../tasks/task-25.2%20-%20RFC-19-phase-3-layer-open-info-close-and-a-batched-layer.features.md) → [TASK-25.3](../../tasks/task-25.3%20-%20RFC-19-phase-4-render_map-and-export_features-against-real-QGIS.md).

The independent SDK CLI architecture path is [TASK-26](../../tasks/task-26%20-%20Refactor-qgis-sdk-CLI-onto-the-shared-Rust-engine-wire-protocol.md). It shares D09's envelope conventions but must not be conflated with the QGIS-native manager.

## Phase 0 — Architectural foundation

The original D01–D08 records were generated as proposals. Their current
reconciliation is recorded in the migration map and summarized here:

| Decision | Disposition | Current owner |
|---|---|---|
| D01 — two-crate architecture | Superseded by the current `qgis-sys` + `qgis-render`/engine workspace layout | TASK-27; architecture.md |
| D02 — ownership model | Still open for a future safe QGIS wrapper; RFC 19 uses manager-owned IDs under D12 | TASK-8, TASK-10, TASK-25.1 |
| D03 — error handling | Qualified/superseded at the transport boundary by D09/D12; legacy qgis-sys side-channel work remains | TASK-9, TASK-25.1 |
| D04 — API priority | Still useful as a planning principle; its tiers are executable in TASK-5 through TASK-12 | TASK-27 |
| D05 — threading | Qualified by D12: QGIS remains single-owner, while the manager exposes a blocking owner queue | TASK-25.4, TASK-25.1 |
| D06 — string strategy | Still open as a performance policy; batching is mandatory for manager feature access | TASK-9, TASK-25.2 |
| D07 — Rust plugins via PyO3 | Superseded as the whole-product direction; retained as rationale for Rust acceleration | TASK-16, TASK-26 |
| D08 — standalone rendering | Still open as an implementation/product direction; the pure-Rust renderer exists, QGIS backend work remains | TASK-12, TASK-25.3 |
| D09–D12 | Accepted active decisions | TASK-20, TASK-24, TASK-25, TASK-26 |

## Phase 1 — Data access

Bind the types needed to read features from a layer. These are tracked in
Backlog.md rather than by a status table here:

- `QgsFields` / `QgsField` → [TASK-5](../../tasks/task-5%20-%20Bind-QgsFields-and-QgsField-schema-types-in-qgis-sys.md)
- `QgsFeature` / `QgsGeometry` → [TASK-6](../../tasks/task-6%20-%20Bind-QgsFeature-AttributeValue-conversions-and-QgsGeometry-in-qgis-sys.md)
- `QgsFeatureIterator` / CRS → [TASK-7](../../tasks/task-7%20-%20Bind-QgsFeatureIterator-and-QgsCoordinateReferenceSystem-in-qgis-sys.md)

Validation remains a real GeoPackage fixture with attributes and geometry:

```rust
let layer = VectorLayer::open("points.gpkg", "pts", "ogr")?;
for feature in layer.features() {
    let name = feature.attribute_string("name");
    let geom = feature.geometry();
    println!("{name}: {}", geom.as_wkt()?);
}
```

## Phase 2 — Project and editing

Project ownership and transactional editing are represented by:

- [TASK-10](../../tasks/task-10%20-%20Bind-QgsProject-with-ownership-transfer-semantics-and-QgsFeatureRequest.md) — project and feature requests.
- [TASK-11](../../tasks/task-11%20-%20Bind-QgsVectorLayerEditBuffer-for-transactional-layer-editing.md) — edit-buffer transactions.

The examples in this section are target API design, not claims that the
current crates already expose a `qgis` safe-wrapper crate.

## Phase 3 — Rendering and output

The pure-Rust `qgis-render` surface and CLI are present, while QGIS-backed
project rendering returns a structured unimplemented error until the native
backend is complete. The work is split between:

- [TASK-12](../../tasks/task-12%20-%20Bind-QgsMapSettings-and-QgsMapRendererSequentialJob-for-embedded-rendering.md) — direct rendering bindings.
- [TASK-19](../../tasks/task-19%20-%20End-to-end-integration-test-suite-for-qgis-server-OGC-endpoints.md) — server integration.
- [TASK-25.3](../../tasks/task-25.3%20-%20RFC-19-phase-4-render_map-and-export_features-against-real-QGIS.md) — rendering/export through the native manager.
- [TASK-20](../../tasks/task-20%20-%20Document-the-engine-wire-protocol-in-the-docs-site.md) — public protocol reference.

D12 settles the RFC 19 manager boundary; it does not make QGIS GUI widgets
part of the headless backend.

## Plugin SDK and tooling

The Python SDK, UI scaffolding, testing, packaging, and Rust acceleration are
separate product work:

- [TASK-1](../../tasks/task-1%20-%20Make%20the%20full%20QGIS%20SDK%20test%20suite%20headless%20and%20CI-green.md) through [TASK-4](../../tasks/task-4%20-%20Cover%20real%20QGIS%20network%20and%20task-manager%20integration.md) — runtime and CI proof.
- [TASK-3](../../tasks/task-3%20-%20Document%20and%20scaffold%20the%20declarative%20plugin%20and%20SDK%20APIs.md) — SDK documentation/scaffolds.
- [TASK-13](../../tasks/task-13%20-%20Implement-ergonomic-PyQGIS-wrappers-for-iface-layers-and-CRS.md) through [TASK-18](../../tasks/task-18%20-%20Add-frontend-framework-starter-templates-for-WebEngine-plugins.md) — SDK API, acceleration, packaging, and UI.
- [TASK-23](../../tasks/task-23%20-%20Refactor-every-test-suite-onto-property-based-and-fixture-driven-testing.md) — property and fixture migration.
- [TASK-26](../../tasks/task-26%20-%20Refactor-qgis-sdk-CLI-onto-the-shared-Rust-engine-wire-protocol.md) — native CLI ownership.

## SDK planning input

The SDK planning bands are retained here as historical planning input; the
milestone and task records are authoritative for current priority, status, and
scope.

| Planning band | Backlog ownership |
|---|---|
| Former Phase 1 — Python-only SDK | `m-3`: TASK-1–TASK-4, TASK-3, TASK-13, TASK-17, TASK-18 |
| Former Phase 2 — Rust acceleration | `m-3`: TASK-16 and TASK-26 |
| Former Phase 3 — rendering integration | `m-2`: TASK-12, TASK-19, TASK-25.3; `m-3`: TASK-26 |

The former estimate was 20–27 weeks across SDK foundations, wrappers, CLI,
testing, templates, Rust acceleration, cross-platform builds, backend
selection, CI templates, and documentation. It is not a delivery commitment;
use the linked tasks and milestone progress instead.

## What remains deliberately out of scope

- GUI widgets and desktop UI objects in the standalone native manager.
- A second hand-maintained protocol for the same qgis-py/qgis-node engine.
- Crash recovery inside the in-process C ABI; D12 defers that to a future subprocess design.
- Historical implementation status in this roadmap. Use the linked Backlog tasks.

## Decision log

- [D01–D08 reconciliation](../knowledge-backlog-map/doc-1%20-%20Knowledge-to-backlog-migration-map.md#decision-record-dispositions)
- [D09 — Wire Protocol over FFI](../../../.knowledge/decisions/D09-wire-protocol-over-ffi.md)
- [D10 — xtask over Shell Scripts](../../../.knowledge/decisions/D10-xtask-over-shell-scripts.md)
- [D11 — Tests Outside `src/`](../../../.knowledge/decisions/D11-tests-outside-src.md)
- [D12 — QGIS Native Manager over the C ABI](../../../.knowledge/decisions/D12-qgis-native-manager-over-c-abi.md)
