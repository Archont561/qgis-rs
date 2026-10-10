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

The repository contains a standalone GIS engine and CLI, Python and Node bindings, and a Python/PyQt SDK that runs inside QGIS. The plugin tooling CLI belongs to that SDK and is pure Python; the Rust-backed implementation this record originally described was retired by [D15](D15-qgis-sdk-cli-pure-python-typer.md). They share Rust code, but they do not have the same runtime owner, input/output contract, or dependency requirements.

The standalone `qgis-rs` package must remain usable without importing PyQGIS. The QGIS plugin SDK must run with the Python and Qt ABI supplied by the host QGIS installation. A direct dependency from `qgis-sdk` to `qgis-py` would couple two different extensions and make plugin installation depend on a separate standalone-engine wheel.

The full product specification is [doc-7 — Rust CLI, Cross-Language FFI, and QGIS SDK Product Boundaries](../../backlog/docs/architecture/doc-7%20-%20Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md).

## Decision

> **Amended by [D15](D15-qgis-sdk-cli-pure-python-typer.md).** `qgis-sdk` is the plugin CLI, a pure-Python typer application. The second name and the alias are retired. The enforcement table below reflects that.

### 1. Separate product responsibilities

- `qgis-cli` executes GIS work: inspection, validation, tile planning, batch planning, rendering, export, and serving.
- `qgis-sdk` is the canonical plugin-development CLI: scaffolding, metadata, validation, build, test, development, packaging, bridge generation, installation, and publishing. It is a pure-Python typer application (D15).
- No second name exists for the plugin CLI (D15).
- `qgis_py` is the standalone Python client for the Rust engine.
- `qgis_sdk` is the QGIS-hosted Python plugin SDK and uses PyQGIS/PyQt for live QGIS objects, UI, Processing, tasks, feedback, and lifecycle.
- `@archont561/qgis-sdk` is the WebEngine/QWebChannel client and is separate from the Node native addon.

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

qgis_py._core -> qgis-engine
```

`qgis-sdk` is absent from that graph because it has no Rust at all. D15 §3 as
amended by TASK-57 removes every Rust path from it: `crates/qgis-sdk` and
`crates/qgis-sdk-core` were deleted in `2d8d69a`, there is no `qgis_sdk._core`
extension, and the CLI is a typer application at
`py-packages/qgis-sdk/src/qgis_sdk/cli.py`. The edges this record used to draw
from `qgis-sdk-core` to `qgis-protocol` describe crates that do not exist.

`qgis-sdk` must not directly depend on `qgis-py`. Removing the SDK Rust crate
alone does not enforce Python dependency or import boundaries: TASK-43 audits
those against D15, while TASK-63 separately owns the reverse import probe.
The optional-acceleration adapter this section allowed is ruled out too — a
plugin that wants a Rust hot path builds and ships its own extension, outside
the SDK.

### 4. Keep CLI and FFI contracts separate

This separation is about `qgis-cli`, the GIS-execution CLI, which stays Rust (D15 §1). It owns argument parsing, terminal output, process signals, exit codes, progress presentation, and subprocess orchestration. FFI owns structured requests, structured responses, typed host wrappers, and host-language exceptions.

The plugin CLI is not a launcher and is not covered by this section. `qgis-sdk` parses its own arguments in Python with typer, and `qgis-plugin` is retired rather than forwarded (D15 §1). The thin launchers this record permitted were built for it and have since been removed from both `qgis-py` (`47a909a`) and `qgis-node` (`41b02b4`), so no Python or npm distribution ships a launcher for a Rust binary today. What survives is the rule behind them: a launcher preserves arguments, stdout, stderr, signals and exit codes, and never implements fallback command semantics.

### 5. Keep QGIS ownership explicit

Pure Rust CLI operations require no QGIS, Python, Qt, or WebEngine. Native QGIS operations run through the accepted manager owner-thread design and advertise their capabilities explicitly. QGIS-hosted UI, Processing, and plugin lifecycle remain in the Python/PyQt SDK. WebEngine is optional and must not be required by ordinary FFI or UI tests.

## Consequences

### Accepted

- A portable pure-Rust CLI can run in CI and server environments without QGIS.
- Python and Node clients share one protocol and one error vocabulary.
- Plugin developers receive a CLI that matches the Python runtime model of QGIS plugins, with no Rust toolchain, no native extension and no second implementation to drift (D15).
- The QGIS SDK can use native QGIS widgets and Processing without leaking GUI objects into the standalone engine.
- Package and ABI failures are visible as capability or installation errors rather than silent alternate implementations.

### Costs

- There are several named products and package entry points to document.
- Some plugin commands orchestrate Python, QGIS, pytest or frontend tools instead of implementing those ecosystems internally. `cargo` and `maturin` are no longer among them: D15 §3 as amended removed the cargo passthrough, so the plugin CLI drives no Rust build.
- Plugin-owned Rust extensions need their own ABI and capability policy; this is outside the SDK contract, not a requirement to restore an SDK acceleration adapter (D15).
- Shared protocol and cross-language fixtures become release obligations.

## Rejected alternatives

| Alternative | Reason rejected |
| --- | --- |
| Make `qgis-sdk` depend on `qgis-py` | Couples unrelated Python extensions and QGIS's embedded Python ABI to the standalone engine package. |
| Put every SDK command in `qgis-cli` | Mixes GIS execution with plugin source/build/package workflows and creates unclear runtime requirements. |
| Expose `run_cli(argv)` as the FFI API | Mixes process semantics with library semantics and duplicates stdout, stderr, signal, and exit-code handling. |
| Let Python or JavaScript keep fallback command implementations | Creates a second set of answers and allows silent behavior drift from Rust. **Reversed by D15** — with no Rust implementation left to drift from, Python is the single answer for the plugin CLI rather than a fallback. The rule that survives is the reason this row existed: one implementation, never two. |
| Expose QGIS/Qt pointers through Python or Node native addons | Violates ownership, thread-affinity, serialization, and host-lifecycle rules. |

## What a gate enforces, and what it cannot

Four of the rules above are facts about manifests, so `pixi run xtask check-boundaries` decides
them on every gate run (TASK-40), and the rest of this record is a claim a reviewer has to check:

| Rule | Enforced by | How it fails |
| --- | --- | --- |
| §3 `qgis-sdk` must not depend on `qgis-py` | `FORBIDDEN_EDGES` — retired: `qgis-sdk` has no Rust crate (D15) | not applicable |
| §4 binding crates own no process semantics | `BINDING_CRATES` | a `[[bin]]` in `qgis-py` or `qgis-node` |
| §1 one owner per canonical executable | `CANONICAL_BINARIES` | `qgis-cli` declared by nobody or by two crates; `qgis-sdk` is a Python console script (D15) |
| §4 no-fallback policy | `TRACKED_FALLBACKS` | a new `*fallback*` file under `crates/`, `py-packages/` or `ts-packages/` |

The no-fallback rule is an allowlist rather than a prohibition. One fallback predated this
record, `py-packages/qgis-sdk/src/qgis_sdk/_fallback_cli.py`. It was removed with the native
`_core` extension (D15), and the allowlist is now empty. An exception
with a name and an owner is a debt; an exception nobody counted is a second set of answers.

Three things the check deliberately does not decide: whether a binary's *behaviour* matches its
contract (that is a test in the owning package), whether a Python distribution's console scripts
shadow a canonical binary on `PATH` (`py-packages/qgis-sdk` ships only the `qgis-sdk` console script, D15), and whether the host-language wrappers stay thin (a review question).

## Implementation gates

- [TASK-40](../../backlog/tasks/task-40%20-%20Define-Rust-CLI-FFI-and-QGIS-SDK-product-boundaries.md) records and tests the product contract.
- [TASK-41](../../backlog/tasks/task-41%20-%20Build-the-pure-Rust-qgis-cli-capability-surface.md) builds the standalone CLI capabilities.
- [TASK-42](../../backlog/tasks/task-42%20-%20Stabilize-Python-and-Node-FFI-clients-and-CLI-launchers.md) stabilizes FFI client contracts. Its former launcher obligations were retired by owner decision on 2026-10-10; binary distribution remains separate packaging work.
- [TASK-43](../../backlog/tasks/task-43%20-%20Separate-qgis-sdk-hosted-runtime-from-qgis-rs-and-qgis-py.md) enforces pure-Python SDK dependency and hosted-runtime boundaries under D15. Its former SDK-extension and acceleration requirements were retired by owner decision on 2026-10-10.
- [TASK-44](../../backlog/tasks/task-44%20-%20Package-the-Rust-native-qgis-plugin-and-qgis-sdk-CLI.md) packaged the plugin CLI. Its Rust-native framing is superseded by D15, and its dependency on TASK-26 was dropped when that task was archived.
- TASK-26, the shared Rust/wire CLI refactor, is **archived**: D15 §1 and §3 as amended reverse what it was written to do, and the crates it names were deleted in `2d8d69a`. Its one surviving outcome — the CLI path does not import PyQGIS or PyQt — was delivered by TASK-57 and is pinned by `tests/test_cli_task57.py`.

All feature and bug-fix implementation follows the repository refactor and TDD skills. Tests establish public seams before structural changes, implementation proceeds in small red-green-refactor slices, and QGIS/Qt/WebEngine gates remain separate from pure tests.
