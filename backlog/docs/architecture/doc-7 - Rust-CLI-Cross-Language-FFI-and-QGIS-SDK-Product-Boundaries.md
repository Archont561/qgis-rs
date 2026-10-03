---
id: doc-7
type: specification
title: Rust CLI, Cross-Language FFI, and QGIS SDK Product Boundaries
description: "Product and implementation boundaries for the standalone Rust CLI, Python/Node FFI clients, and the QGIS-hosted plugin SDK."
tags: [architecture, cli, ffi, rust, python, node, qgis-sdk, protocol]
status: accepted
date: 2026-10-03
---

# Rust CLI, Cross-Language FFI, and QGIS SDK Product Boundaries

## Purpose

This specification records the product split discussed for qgis-rs. It prevents the standalone GIS engine, the Python/Node bindings, and the QGIS-hosted plugin SDK from accumulating overlapping command semantics or incompatible runtime assumptions.

The governing rule is:

> Rust owns deterministic computation, data movement, orchestration, and protocol behavior. QGIS remains authoritative for QGIS project semantics, providers, Processing, styling, and desktop UI.

The three product surfaces are distinct:

```text
qgis-cli
  Executes GIS work.

qgis-rs Python/Node clients
  Embed the shared Rust engine through one versioned protocol.

qgis-plugin / qgis-sdk CLI
  Develops, tests, packages, and publishes QGIS plugins.

qgis_sdk runtime
  Runs inside QGIS and owns PyQGIS, PyQt, Qt, Processing, and plugin lifecycle.
```

This document complements:

- [D09 — Wire Protocol over FFI](../../../.knowledge/decisions/D09-wire-protocol-over-ffi.md)
- [D12 — QGIS Native Manager over the C ABI](../../../.knowledge/decisions/D12-qgis-native-manager-over-c-abi.md)
- [doc-4 — QGIS Native Manager and API Coverage Strategy](doc-4%20-%20QGIS-Native-Manager-and-API-Coverage-Strategy.md)
- [doc-5 — QGIS SDK Testing Utilities and Cross-Language Bridge Contracts](../testing/doc-5%20-%20QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md)
- [doc-6 — QGIS SDK Native UI Kit and Visual Design Loop Strategy](../ui/doc-6%20-%20QGIS-SDK-Native-UI-Kit-and-Visual-Design-Loop-Strategy.md)

## Product and dependency graph

```text
qgis-protocol
      ^
      |
qgis-engine ------> qgis-render
      ^                    ^
      |                    |
qgis-cli            optional QGIS backend

qgis-sdk-core -----> qgis-protocol
      |              optional qgis-engine/qgis-render reuse
      v
qgis-plugin / qgis-sdk binaries
      v
qgis_sdk._core (optional PyO3 tooling adapter)

qgis_sdk Python runtime -----> qgis, qgis.core, qgis.gui, PyQt/QGIS Qt
```

The standalone bindings are sibling adapters:

```text
qgis_rs._core      -> qgis-engine -> qgis-render/native manager
qgis-node addon    -> qgis-engine -> qgis-render/native manager
qgis_sdk._core     -> qgis-sdk-core
qgis_sdk runtime   -> PyQGIS/PyQt inside the QGIS host
```

`qgis-sdk` must not directly depend on `qgis-py`. The two are different products and different Python environments. Shared Rust behavior is reused through `qgis-protocol`, `qgis-engine`, `qgis-render`, or an explicit SDK-core crate, never by loading one binding extension from another.

## Standalone `qgis-cli`

### Audience and runtime

`qgis-cli` serves GIS operators, data engineers, CI jobs, server operators, and batch workflows. Its baseline executable is pure Rust and does not require Python, PyQGIS, Qt, or Node. An optional native QGIS backend may add full QGIS behavior; unavailable native capabilities must be reported explicitly rather than silently replaced.

The CLI is a process boundary:

```text
argv -> parse -> engine operation -> artifact/report -> stdout/stderr -> exit code
```

The FFI is a library boundary and does not own CLI parsing or terminal behavior.

### Core capabilities

Pure Rust capabilities should include:

- `version`: CLI, engine, transport, target, and backend versions;
- `capabilities`: supported operations, backend availability, limits, and optional QGIS version;
- `doctor`: explain missing tools, libraries, backends, profiles, or runtime configuration;
- `validate`: extents, CRS identifiers, zoom ranges, tile bounds, render settings, output formats, batch manifests, and operation requests;
- `inspect`: basic project/container/XML manifests and declared metadata, with explicit `qgis_validation: not_performed` when QGIS was not used;
- `tiles plan`: tile ranges, bounds, counts, estimates, and deterministic manifests;
- `batch plan`: reproducible execution plans, job IDs, output paths, and cache keys;
- pure Rust geometry, data validation, conversion, and statistics for explicitly supported formats;
- deterministic artifact manifests, atomic output policy, caching, resume, resource limits, and cancellation.

Optional native-backed capabilities may include:

- full QGIS project validation;
- full QGIS-styled map and print-layout rendering;
- provider-backed feature access and export;
- QGIS expressions and coordinate transforms;
- tile rendering;
- Processing execution;
- WMS/WFS/OGC service behavior.

Native-backed operations are owned by the native manager and exposed only when the capability manifest says they are available.

### Command ownership

```text
qgis-cli version
qgis-cli capabilities
qgis-cli doctor
qgis-cli validate
qgis-cli inspect
qgis-cli tiles plan
qgis-cli batch plan
qgis-cli render              # native backend when enabled
qgis-cli export              # native backend when enabled
qgis-cli serve               # backend-specific service
```

`qgis-cli` does not scaffold plugins, create `metadata.txt`, install a plugin into QGIS, generate WebChannel declarations, or publish to the QGIS Plugin Repository.

### CLI contract

Every command should support machine-readable output where meaningful:

- `--json` for structured output;
- stable exit-code categories;
- diagnostics on stderr, never mixed into JSON stdout;
- deterministic locale-independent formatting;
- explicit overwrite and filesystem policy;
- dry-run mode;
- configurable workers and resource limits;
- SIGINT cancellation;
- no implicit network access.

Suggested exit categories are:

```text
0   success
2   invalid command or arguments
10  invalid input
11  missing input
12  unavailable backend
13  operation failure
14  filesystem or artifact failure
15  cancelled
20  protocol or internal engine failure
```

## Python and Node FFI clients

### Native boundary

`crates/qgis-py` and `crates/qgis-node` remain thin adapters. Their native surfaces are:

```rust
invoke(request_json) -> response_json
transport_version() -> u32
```

No per-domain `#[pyclass]` or `#[napi]` mirror is added. New functionality is added to `qgis-protocol` and `qgis-engine`, then exposed through host-language wrappers.

The protocol remains the single contract:

- versioned JSON envelope;
- closed operation vocabulary;
- `snake_case` wire keys;
- structured error kinds;
- JSON-safe values;
- opaque manager IDs for live QGIS objects;
- path-plus-metadata artifacts;
- paged or streamed bulk results rather than per-feature crossings.

### Shared FFI capabilities

Both clients should be able to reach:

- transport and engine discovery;
- pure extent, CRS, geometry, zoom, and tile operations;
- project manifest inspection;
- batch planning and validation;
- native project, layer, feature, render, and export operations when the manager is available;
- capability/version reporting;
- structured errors and cancellation for long-running work.

QGIS-specific values use explicit tagged representations. Raw `QVariant`, `QObject *`, `QWidget *`, QGIS pointers, and Qt objects never cross the boundary.

Large results use pages, cursors, bounded arrays, or path-based artifacts. Rendering and export return artifact metadata, not unbounded base64 payloads.

### Python client

`qgis_rs` is a standalone engine client. Its ergonomic surface may provide `Extent`, `Crs`, `TilePlan`, `Project`, render settings, typed errors, `PathLike` support, context managers, paged iterators, capability discovery, and a documented raw `invoke` escape hatch.

The PyO3 adapter releases the GIL while Rust performs work that does not touch Python objects. It has no PyQGIS or PyQt dependency.

`qgis_sdk` is different: its hosted runtime uses `qgis.core`, `qgis.gui`, PyQt, and QGIS lifecycle rules. It does not route UI, Processing, or live QGIS objects through `qgis_rs._core`.

Optional Rust acceleration for a plugin may be provided through an explicit SDK acceleration adapter. It must remain optional because QGIS controls the embedded Python ABI.

### Node client

The `qgis-rs` Node package provides typed TypeScript wrappers over the same engine. It may use camelCase names at the JavaScript edge while retaining `snake_case` on the wire.

It should provide:

- typed results and `QgisError`;
- synchronous APIs for cheap pure operations;
- Promise-based APIs for expensive operations;
- `AbortSignal` cancellation;
- paged async iterators for large feature results;
- artifact paths and metadata;
- a raw `invoke` escape hatch;
- no JavaScript fallback that reimplements Rust algorithms.

`@qgis-sdk/bridge` is separate. It is a QWebChannel/WebEngine client for a QGIS-hosted plugin UI and communicates with an explicitly described Python bridge. It does not provide direct NAPI access to QGIS GUI objects.

## CLI versus FFI

The CLI and FFI share engine operations but have different contracts.

```text
Canonical Rust CLI process
  qgis-cli
    -> qgis-cli library
      -> qgis-engine

Python API
  qgis_rs._core.invoke
    -> qgis-engine

Node API
  qgis-rs NAPI invoke
    -> qgis-engine
```

FFI crates may package a CLI binary, but the addon itself should not expose `run_cli(argv)` as its public native API. CLI parsing, terminal output, signals, progress presentation, and process exit status are process concerns.

Python and npm distributions may ship thin launchers:

```text
qgis-rs Python console script -> canonical qgis-cli executable
qgis-rs npm bin wrapper       -> canonical qgis-cli executable
```

Launchers must preserve arguments, stdout, stderr, signals, and exit status. They must not contain alternate command semantics or silent fallbacks.

## Rust-native `qgis-plugin` / `qgis-sdk` CLI

### Audience and runtime

The plugin CLI serves plugin developers. It consumes a plugin source tree and produces a plugin project, test result, build artifact, or repository package.

```text
qgis-plugin / qgis-sdk
  develops, tests, packages, and publishes plugins
```

The canonical implementation should be Rust. `qgis-plugin` is the canonical executable name; `qgis-sdk` may remain an exact compatibility alias. Both call the same command library and parser.

### Commands

The SDK CLI should own:

```text
qgis-plugin new
qgis-plugin info
qgis-plugin validate
qgis-plugin build
qgis-plugin test
qgis-plugin dev
qgis-plugin install
qgis-plugin package
qgis-plugin publish
qgis-plugin ui add-dialog
qgis-plugin bridge generate
qgis-plugin rust init
qgis-plugin rust build
```

Rust should implement or orchestrate:

- plugin templates and project creation;
- metadata parsing and generation;
- source/resource/package validation;
- UI, WebEngine, and bridge scaffolding;
- TypeScript bridge declaration generation from normalized descriptors;
- deterministic ZIPs, checksums, and artifact manifests;
- frontend, Cargo, maturin, and Python tool invocation;
- QGIS profile launch and headless integration-test setup;
- timeout, cancellation, logging, and exit-code mapping.

The SDK CLI should not import PyQGIS for pure commands. Commands that need QGIS may launch a controlled QGIS/Python process, normally with `QT_QPA_PLATFORM=offscreen`, and must report that runtime requirement explicitly.

The hosted plugin runtime remains Python/PyQGIS/PyQt. Rust CLI generation and test orchestration must not become a second plugin runtime or replace QGIS-owned Processing UI.

### SDK versus standalone CLI

| Concern | `qgis-cli` | `qgis-plugin` / `qgis-sdk` |
| --- | --- | --- |
| Input | project, layer, extent, data, job manifest | plugin source tree |
| Output | map, tiles, features, JSON, service | source tree, test report, wheel, ZIP, metadata |
| User | operator or GIS automation | plugin developer |
| Core | `qgis-engine` and `qgis-render` | `qgis-sdk-core` tooling domain |
| QGIS | optional backend for GIS operations | optional runtime for integration tests/dev launch |
| UI | no plugin UI | generates/tests plugin UI |
| Processing | executes or delegates to QGIS | scaffolds/tests Processing plugin code |
| Publishing | no | QGIS Plugin Repository workflow |

Neither CLI delegates its full command implementation to the other.

## QGIS SDK dependency boundary

The `qgis-sdk` Rust crate may depend directly on `qgis-protocol`, `qgis-engine`, `qgis-render`, or an SDK-core crate where reuse is justified. It must not depend on `qgis-py`.

The `qgis-sdk` Python package has two explicit parts:

1. Hosted runtime: PyQGIS/PyQt-native plugin, UI, Processing, task, and lifecycle APIs.
2. Optional native tooling/acceleration: a separate `qgis_sdk._core` adapter or plugin-specific Rust module.

The standalone `qgis_rs` package remains independently installable. An optional SDK extra may use it for pure Rust acceleration only when the QGIS Python ABI and package availability are validated. The base SDK must not require it.

## Testing and implementation discipline

All implementation tasks follow the repository's refactor and TDD skills:

- Read `.agents/skills/refactor/SKILL.md` before refactoring existing code.
- Read `.agents/skills/tdd/SKILL.md` before implementing a feature or fixing a bug.
- Establish the public seam and characterization/golden test before changing structure.
- Work in small vertical slices: failing behavior test, minimal implementation, passing test, then one refactor.
- Preserve public imports, CLI flags, wire JSON, generated filenames, exit codes, and QGIS lifecycle behavior unless an explicit contract task changes them.
- Keep pure tests independent of QGIS; gate Qt, QGIS, and WebEngine tests separately.
- Use `QT_QPA_PLATFORM=offscreen` and serialized execution for Qt/QGIS tests.

Required test layers include:

```text
Rust unit/integration tests
  qgis-render, qgis-protocol, qgis-engine, qgis-cli, qgis-sdk-core

Cross-language contract tests
  Rust, Python, TypeScript, and native manager shared fixtures

CLI contract tests
  stdout, stderr, exit codes, JSON, filesystem policy, cancellation

QGIS-hosted tests
  PyQGIS/PyQt lifecycle, Processing, UI, WebEngine, and visual evidence
```

A pure Rust or FFI test must not require WebEngine. A failed real UI construction must return a failure and must not print an error before returning `Dialog.Accepted`.

## Capability ownership matrix

| Capability | Pure Rust CLI | Native QGIS backend | `qgis_rs` Python | `qgis-rs` Node | `qgis_sdk` / bridge |
| --- | --- | --- | --- | --- | --- |
| Extent/zoom/tile math | yes | optional | yes | yes | not primary |
| Pure geometry/data subset | yes | optional | yes | yes | optional |
| Project manifest | yes | yes | yes | yes | optional |
| Full QGIS validation | no | yes | via backend | via backend | via QGIS |
| Full QGIS styling/rendering | no | yes | via backend | via backend | UI preview |
| Feature paging/export | pure formats | yes | via backend | via backend | via bridge if needed |
| Processing | no | yes | hosted/native API | bridge or manager | yes |
| Native Qt/QGIS widgets | no | manager-owned only | `qgis_sdk.ui` | no | WebEngine bridge |
| Plugin lifecycle | no | no | `qgis_sdk` | no | bridge/UI layer |
| Plugin scaffolding/package | no | no | SDK wrapper | optional wrapper | no |

## Implementation sequence

1. Define and test this product and dependency contract.
2. Stabilize pure `qgis-cli` discovery, validation, inspection, tile planning, batch planning, errors, artifacts, and backend gates.
3. Stabilize shared protocol fixtures and Python/Node FFI clients.
4. Build the Rust-native `qgis-sdk-core` CLI and make `qgis-plugin`/`qgis-sdk` share one implementation.
5. Remove duplicated Python/JavaScript CLI semantics and silent fallbacks.
6. Separate `qgis_sdk` hosted runtime from standalone `qgis_rs` and add optional acceleration boundaries.
7. Integrate the native manager and QGIS-hosted UI/Processing behavior behind explicit capabilities.

## Non-goals

- One hand-written stable ABI for every QGIS C++ class and method;
- exposing QGIS pointers or Qt objects through Python/Node native addons;
- making PyQGIS a dependency of the standalone CLI path;
- requiring WebEngine for ordinary UI or bridge tests;
- replacing QGIS's Processing parameter UI with a parallel implementation;
- maintaining independent Python, JavaScript, and Rust command semantics;
- promising in-process crash recovery from QGIS memory faults.
