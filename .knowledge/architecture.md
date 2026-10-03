---
type: Architecture
title: Architecture
description: Crate layout, layer model, and FFI data flow for qgis-rs.
status: stable
tags: [architecture, crate, layers, ffi, protocol]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# Architecture

## Current crate model

The workspace has a Rust engine, a versioned transport, language adapters, and
an optional native QGIS backend. Backlog.md owns implementation status and
acceptance criteria; this document describes the stable boundaries and the
rationale behind them.

| Crate | Purpose |
|---|---|
| `qgis-sys` | Native-manager C ABI for QGIS lifecycle, registry, and copied protocol values |
| `qgis-render` | Backend-agnostic domain engine: extents, CRS, tiles, projects, render settings |
| `qgis-protocol` | Versioned JSON envelope and closed operation/error vocabulary |
| `qgis-engine` | One `invoke(request_json) -> response_json` dispatcher over `qgis-render` |
| `qgis-py` / `qgis-node` | Thin PyO3/NAPI adapters over the shared engine invoke |
| `qgis-server` | HTTP surface for WMS/WFS/OGC API work |
| `qgis-mcp` / `qgis-cli` | MCP and command-line surfaces over the engine |
| `qgis-sdk` | Rust-native plugin SDK CLI/core, separate from the QGIS-hosted plugin runtime |
| `xtask` | Typed repository automation, per D10 |

The original two-crate sketch (`qgis-sys` plus a future `qgis`) is retained in
D01 as historical rationale. There is no `crates/qgis` safe-wrapper crate in
the current workspace; the safe backend-agnostic layer is `qgis-render`, and
its QGIS-backed operations currently return `Error::Unimplemented` until the
backend work in [TASK-25.3](../backlog/tasks/task-25.3%20-%20RFC-19-phase-4-render_map-and-export_features-against-real-QGIS-no-NEEDS_QGIS.md)
lands.

## Execution map

- The RFC 19 architecture gate is [TASK-25.4](../backlog/tasks/task-25.4%20-%20RFC-19-resolve-open-questions-and-record-the-native-manager-ADR.md), recorded in [D12](decisions/D12-qgis-native-manager-over-c-abi.md).
- The C++ toolchain prerequisite is [TASK-24](../backlog/tasks/task-24%20-%20Add-cmake-and-ninja-to-the-C-toolchain-dependencies.md).
- The native manager/lifecycle sequence is [TASK-25.1](../backlog/tasks/task-25.1%20-%20RFC-19-phase-2-native-manager-ID-registry-and-lifecycle-behind-qgis_invoke.md) → [TASK-25.2](../backlog/tasks/task-25.2%20-%20RFC-19-phase-3-layer-open-info-close-and-a-batched-layer.features.md) → [TASK-25.3](../backlog/tasks/task-25.3%20-%20RFC-19-phase-4-render_map-and-export_features-against-real-QGIS-no-NEEDS_QGIS.md).
- The independent SDK CLI boundary is [TASK-26](../backlog/tasks/task-26%20-%20Refactor-qgis-sdk-CLI-onto-the-shared-Rust-engine-wire-protocol.md), with the accepted product/dependency contract in [doc-7](../backlog/docs/architecture/doc-7%20-%20Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md) and implementation decomposition in TASK-40 through TASK-44.

## Layer organization

`qgis-sys` has one QGIS implementation unit and one Rust C-ABI adapter:

```
src/
├── lib.rs                         # native-manager module export
└── native_manager/manager.cpp    # sole QGIS-header owner and JSON dispatcher
include/
└── native_manager/manager.h      # qgis_invoke/qgis_free/version declarations
```

The manager owns QGIS objects on its dedicated thread. It accepts copied JSON
requests, stores layers behind integer registry IDs, and returns copied JSON
values or structured error envelopes. There are no per-class CXX bridges or
raw QGIS handles in the public Rust surface.

## FFI and transport data flow

### Native manager path

```
Python / Node / Rust caller
  │ JSON text
  ▼
qgis-py / qgis-node → qgis-engine
  │
  ├── pure-Rust operation
  └── qgis-sys native manager → QGIS owner thread
```

The native manager is compiled as one C++ translation unit. Its only default
visible symbols are `qgis_invoke`, `qgis_free`, and
`qgis_transport_version`; QGIS pointers and Qt values never cross that boundary.

### D09 wire path

```
Python / Node / Rust caller
  │ JSON text
  ▼
qgis-py / qgis-node → qgis-engine
  │
  ▼
qgis-protocol envelope + qgis-render operation
  │
  ├── pure-Rust operation
  └── future QGIS operation → RFC 19 native manager
```

D09 makes the JSON protocol the API across language bindings. D12 extends that
contract to the native manager: QGIS objects stay behind one owner thread,
handles are integer IDs, binary artifacts are paths plus metadata, and an
in-process C ABI does not promise crash recovery.

The manager is exposed to Rust through
`qgis_sys::native_manager_ffi::invoke`, which owns the C ABI response/free pair.
`app_init` and `engine_info` establish the manager lifecycle; layer operations
use integer IDs and return copied metadata, never QGIS pointers. Concurrent
callers are copied into a blocking owner-thread queue.

## Ownership and handles

The manager's registry owns each `QgsVectorLayer` in a `unique_ptr` vector and
keeps a private integer-to-pointer index only on the owner thread. `layer_open`
returns the integer ID, `layer_info` and `layer_features` return copied values,
and `layer_close` or owner-thread shutdown destroys the object. No opaque QGIS
handle is exposed to Rust or a language binding.

## Architecture decisions

- [D01–D08 reconciliation](../backlog/docs/knowledge-backlog-map/doc-1%20-%20Knowledge-to-backlog-migration-map.md#decision-record-dispositions)
- [D09 — Wire Protocol over FFI](decisions/D09-wire-protocol-over-ffi.md)
- [D10 — xtask over Shell Scripts](decisions/D10-xtask-over-shell-scripts.md)
- [D11 — Tests Outside `src/`](decisions/D11-tests-outside-src.md)
- [D12 — QGIS Native Manager over the C ABI](decisions/D12-qgis-native-manager-over-c-abi.md)
