---
type: Concept
title: QGIS Vector Layer
description: "QgsVectorLayer lifecycle and copied feature access through the RFC 19 native manager."
status: stable
tags: [qgis, vector-layer, geo, features, native-manager]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# QGIS Vector Layer

## Current boundary

Direct per-class CXX shims were retired after RFC 19 phase 3. Vector layers are
manager-owned QGIS objects addressed by an integer `layer_id`; no QGIS pointer,
Qt value, or opaque CXX handle crosses the Rust or JSON boundary. The manager
serializes all operations on its dedicated QGIS owner thread.

| Operation | Result | Purpose |
|---|---|---|
| `layer_open` | `layer_id`, `is_valid`, `name` | Open a provider-backed vector layer |
| `layer_info` | copied metadata and fields | Read name, validity, feature count, CRS, geometry type, and schema in one crossing |
| `layer_features` | bounded feature page | Copy feature IDs, JSON-safe attributes, and WKT geometry in one manager crossing |
| `layer_close` | `closed` | Release the registry entry and owned QGIS layer |

The manager returns `invalid_object_id` for missing or already-closed IDs. A
page accepts `offset` and `limit` (default 100, maximum 1000), and reports
`next_offset` when more features remain. Feature iteration happens inside the
manager; clients do not issue one request per feature.

## Fixture

`crates/qgis-sys/tests/fixtures/points.gpkg` contains three EPSG:4326 point
features with fields `fid` and `name`. The canonical request and copied values
live in [`test-fixtures/layer-lifecycle.json`](../test-fixtures/layer-lifecycle.json)
and are asserted by the Rust protocol, Python, and TypeScript suites.

## Lifecycle

`app_init` starts the owner thread and QGIS application. `app_shutdown` clears
the registry on that owner thread before calling `exitQgis`, and reports how
many open layers it released. `native_manager_shutdown.rs` proves that anbandoned layer is released rather than leaked through process teardown.

Future manager work includes rendering and feature export in [TASK-25.3](../backlog/tasks/task-25.3%20-%20RFC-19-phase-4-render_map-and-export_features-against-real-QGIS-no-NEEDS_QGIS.md).
