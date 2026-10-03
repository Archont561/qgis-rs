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
| `qgis-sys` | Low-level QGIS/Qt FFI shims; currently CXX-based and being migrated for RFC 19 |
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
backend work in [TASK-12](../backlog/tasks/task-12%20-%20Bind-QgsMapSettings-and-QgsMapRendererSequentialJob-for-embedded-rendering.md)
and [TASK-25.3](../backlog/tasks/task-25.3%20-%20RFC-19-phase-4-render_map-and-export_features-against-real-QGIS-no-NEEDS_QGIS.md)
lands.

## Execution map

- The RFC 19 architecture gate is [TASK-25.4](../backlog/tasks/task-25.4%20-%20RFC-19-resolve-open-questions-and-record-the-native-manager-ADR.md), recorded in [D12](decisions/D12-qgis-native-manager-over-c-abi.md).
- The C++ toolchain prerequisite is [TASK-24](../backlog/tasks/task-24%20-%20Add-cmake-and-ninja-to-the-C-toolchain-dependencies.md).
- The native manager/lifecycle sequence is [TASK-25.1](../backlog/tasks/task-25.1%20-%20RFC-19-phase-2-native-manager-ID-registry-and-lifecycle-behind-qgis_invoke.md) → [TASK-25.2](../backlog/tasks/task-25.2%20-%20RFC-19-phase-3-layer-open-info-close-and-a-batched-layer.features.md) → [TASK-25.3](../backlog/tasks/task-25.3%20-%20RFC-19-phase-4-render_map-and-export_features-against-real-QGIS-no-NEEDS_QGIS.md).
- The independent SDK CLI boundary is [TASK-26](../backlog/tasks/task-26%20-%20Refactor-qgis-sdk-CLI-onto-the-shared-Rust-engine-wire-protocol.md).

## Layer organization

Inside `qgis-sys`, code is organized by QGIS module layer:

```
src/
├── lib.rs            # module tree root + ffi re-exports
└── core/             # maps to QGIS "core" library (libqgis_core)
    ├── application/  # QgsApplication, app info
    ├── vector_layer/ # QgsVectorLayer
    ├── geometry/     # future geometry bindings
    └── ...
```

Each concept directory contains:

- `mod.rs` — Rust module declaration
- `<short>.rs` — `#[cxx::bridge]` while the current qgis-sys boundary remains CXX
- `<short>.cpp` — C++ implementation

The RFC 19 migration will add one native manager translation unit and a C ABI;
that target is constrained by [D12](decisions/D12-qgis-native-manager-over-c-abi.md)
and must not turn into a second per-concept wire surface.

## FFI and transport data flow

### Current CXX shim path

```
Rust caller
  │
  ▼
#[cxx::bridge] ──► generated CXX glue
  │
  ▼
C++ shim (`qgis-sys/src/**/*.cpp`)
  │
  ▼
QGIS C++ API (`libqgis_core`)
```

Headers remain clean: `include/core/*.h` declares opaque handles and
signatures without including QGIS headers. Shims contain the QGIS includes,
catch exceptions, and convert Qt strings to primitives. The build details are
in [build-system.md](build-system.md); the CMake/Ninja environment prerequisite
is [TASK-24](../backlog/tasks/task-24%20-%20Add-cmake-and-ninja-to-the-C-toolchain-dependencies.md).

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

## Ownership and handles

The current CXX handle pattern is:

1. The header declares `QGIS_DECLARE_HANDLE(FooHandle)` with an opaque pointer.
2. C++ defines the handle destructor with `QGIS_DEFINE_HANDLE_DTOR`.
3. C++ uses `real()` / `real_const()` helpers to access the QGIS object.
4. Rust sees the handle as an opaque CXX type held through `UniquePtr`.

This pattern remains valid for the existing qgis-sys implementation. RFC 19
uses a different ownership surface: the manager owns QGIS objects in an ID
registry, and only integer IDs cross the JSON/C boundary. The relevant
ownership rationale is in [D02](decisions/D02-ownership-model.md) and the
accepted manager rule is in [D12](decisions/D12-qgis-native-manager-over-c-abi.md).

## Architecture decisions

- [D01–D08 reconciliation](../backlog/docs/knowledge-backlog-map/doc-1%20-%20Knowledge-to-backlog-migration-map.md#decision-record-dispositions)
- [D09 — Wire Protocol over FFI](decisions/D09-wire-protocol-over-ffi.md)
- [D10 — xtask over Shell Scripts](decisions/D10-xtask-over-shell-scripts.md)
- [D11 — Tests Outside `src/`](decisions/D11-tests-outside-src.md)
- [D12 — QGIS Native Manager over the C ABI](decisions/D12-qgis-native-manager-over-c-abi.md)
