---
type: Decision
id: D13
title: Rust CLI, FFI, and QGIS SDK product boundaries
description: "Keep GIS execution, cross-language embedding, plugin tooling, and QGIS-hosted runtime as separate products with shared Rust protocol components."
status: accepted
tags: [architecture, cli, ffi, qgis-sdk, python, node, rust]
date: 2026-10-03
---

# D13: Rust CLI, FFI, and QGIS SDK product boundaries

## Context

The repository contains a standalone GIS engine and CLI, Python and Node bindings, a Rust-backed plugin tooling CLI, and a Python/PyQt SDK that runs inside QGIS. They share Rust code, but they do not have the same runtime owner, input/output contract, or dependency requirements.

The standalone `qgis-rs` package must remain usable without importing PyQGIS. The QGIS plugin SDK must run with the Python and Qt ABI supplied by the host QGIS installation. A direct dependency from `qgis-sdk` to `qgis-py` would couple two different extensions and make plugin installation depend on a separate standalone-engine wheel.

The full product specification is [doc-7 — Rust CLI, Cross-Language FFI, and QGIS SDK Product Boundaries](../../backlog/docs/architecture/doc-7%20-%20Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md).

## Decision

### 1. Separate product responsibilities

- `qgis-cli` executes GIS work: inspection, validation, tile planning, batch planning, rendering, export, and serving.
- `qgis-plugin` is the canonical plugin-development CLI: scaffolding, metadata, validation, build, test, development, packaging, bridge generation, installation, and publishing.
- `qgis-sdk` may be an exact compatibility alias for `qgis-plugin`; it must not have a second parser or reduced implementation.
- `qgis_rs` is the standalone Python client for the Rust engine.
- `qgis_sdk` is the QGIS-hosted Python plugin SDK and uses PyQGIS/PyQt for live QGIS objects, UI, Processing, tasks, feedback, and lifecycle.
- `@qgis-sdk/bridge` is the WebEngine/QWebChannel client and is separate from the Node native addon.

### 2. Keep the FFI thin

`qgis-py` and `qgis-node` expose the versioned protocol through `invoke(request_json) -> response_json` and transport-version discovery. They do not mirror every Rust or QGIS type as native binding classes, expose `argv` as a native API, or carry QGIS/Qt pointers across the boundary.

Host-language wrappers provide typed and idiomatic APIs over the protocol. Bulk data uses pages, cursors, or artifact metadata. QGIS manager handles are opaque IDs. The protocol, not any binding crate, is the source of truth.

### 3. Share Rust components without making binding dependencies

The dependency direction is:

```text
qgis-protocol <- qgis-engine <- qgis-render
                       ^
                       |
                    qgis-cli

qgis-sdk-core -> qgis-protocol
qgis-sdk-core may reuse qgis-engine/qgis-render where useful
qgis_sdk._core -> qgis-sdk-core
qgis_rs._core -> qgis-engine
```

`qgis-sdk` must not directly depend on `qgis-py`. Optional plugin acceleration may use a separately validated Rust engine adapter, but the base SDK must not require `qgis-rs` or its PyO3 extension.

### 4. Keep CLI and FFI contracts separate

The canonical Rust CLI owns argument parsing, terminal output, process signals, exit codes, progress presentation, and subprocess orchestration. FFI owns structured requests, structured responses, typed host wrappers, and host-language exceptions.

Python and npm distributions may ship thin launchers for the canonical Rust binaries. Launchers preserve arguments, stdout, stderr, signals, and exit codes; they do not implement fallback command semantics.

### 5. Keep QGIS ownership explicit

Pure Rust CLI operations require no QGIS, Python, Qt, or WebEngine. Native QGIS operations run through the accepted manager owner-thread design and advertise their capabilities explicitly. QGIS-hosted UI, Processing, and plugin lifecycle remain in the Python/PyQt SDK. WebEngine is optional and must not be required by ordinary FFI or UI tests.

## Consequences

### Accepted

- A portable pure-Rust CLI can run in CI and server environments without QGIS.
- Python and Node clients share one protocol and one error vocabulary.
- Plugin developers receive a Rust-native CLI without changing the Python runtime model of QGIS plugins.
- The QGIS SDK can use native QGIS widgets and Processing without leaking GUI objects into the standalone engine.
- Package and ABI failures are visible as capability or installation errors rather than silent alternate implementations.

### Costs

- There are several named products and package entry points to document.
- Some plugin commands orchestrate Python, QGIS, Cargo, maturin, or frontend tools instead of implementing those ecosystems internally.
- Optional acceleration needs explicit ABI and capability checks.
- Shared protocol and cross-language fixtures become release obligations.

## Rejected alternatives

| Alternative | Reason rejected |
| --- | --- |
| Make `qgis-sdk` depend on `qgis-py` | Couples unrelated Python extensions and QGIS's embedded Python ABI to the standalone engine package. |
| Put every SDK command in `qgis-cli` | Mixes GIS execution with plugin source/build/package workflows and creates unclear runtime requirements. |
| Expose `run_cli(argv)` as the FFI API | Mixes process semantics with library semantics and duplicates stdout, stderr, signal, and exit-code handling. |
| Let Python or JavaScript keep fallback command implementations | Creates a second set of answers and allows silent behavior drift from Rust. |
| Expose QGIS/Qt pointers through Python or Node native addons | Violates ownership, thread-affinity, serialization, and host-lifecycle rules. |

## Implementation gates

- [TASK-40](../../backlog/tasks/task-40%20-%20Define-Rust-CLI-FFI-and-QGIS-SDK-product-boundaries.md) records and tests the product contract.
- [TASK-41](../../backlog/tasks/task-41%20-%20Build-the-pure-Rust-qgis-cli-capability-surface.md) builds the standalone CLI capabilities.
- [TASK-42](../../backlog/tasks/task-42%20-%20Stabilize-Python-and-Node-FFI-clients-and-CLI-launchers.md) stabilizes FFI clients and launchers.
- [TASK-43](../../backlog/tasks/task-43%20-%20Separate-qgis-sdk-hosted-runtime-from-qgis-rs-and-qgis-py.md) enforces the hosted-runtime dependency boundary.
- [TASK-44](../../backlog/tasks/task-44%20-%20Package-the-Rust-native-qgis-plugin-and-qgis-sdk-CLI.md) packages the canonical plugin CLI and exact alias.
- [TASK-26](../../backlog/tasks/task-26%20-%20Refactor-qgis-sdk-CLI-onto-the-shared-Rust-engine-wire-protocol.md) implements the shared Rust/wire CLI refactor.

All feature and bug-fix implementation follows the repository refactor and TDD skills. Tests establish public seams before structural changes, implementation proceeds in small red-green-refactor slices, and QGIS/Qt/WebEngine gates remain separate from pure tests.
