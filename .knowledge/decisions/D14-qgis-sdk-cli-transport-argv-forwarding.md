---
type: Decision
id: D14
title: qgis-sdk CLI transport — native argv forwarding; capabilities over the wire protocol
description: "The Python qgis-sdk CLI forwards raw argv to one `cli_main` pyfunction in the `_core` extension and parses nothing; engine capabilities cross the D09 wire protocol."
status: superseded
superseded_by: D15
tags: [architecture, cli, ffi, pyo3, qgis-sdk, python, rust]
date: 2026-10-09
---

# D14: qgis-sdk CLI transport — native argv forwarding; capabilities over the wire protocol

> **Superseded by [D15 — qgis-sdk CLI is pure Python on typer and questionary](D15-qgis-sdk-cli-pure-python-typer.md).** The decision below is kept as the record of what was accepted on 2026-10-09. The `_core` transport and the Rust CLI it describes have been removed.

## Context

The qgis-sdk Python CLI currently has three overlapping paths: Python command
handlers in `py-packages/qgis-sdk/src/qgis_sdk/cli.py`, a pure-Python
`_fallback_cli.py`, and Rust CLI implementations in
the Rust binaries under `crates/qgis-sdk` and their incomplete sibling delegation. TASK-26 exists to collapse them: command behavior implemented
once in Rust, Python a thin client. D09 fixed the transport for *engine
capabilities* (`invoke(json) -> json` per binding); D13 fixed the product
boundaries (no second parser in the `qgis-sdk` alias; the CLI path stays
independent of PyQGIS). What remained open was the transport for the *CLI
itself*: typed pyfunctions per command, a JSON envelope around argv, or native
argv forwarding.

## Decision

### 1. The CLI transport is native argv forwarding

The maturin-built PyO3 extension `qgis_sdk._core` — already shipped inside the
wheel — exposes one pyfunction:

```rust
#[pyfunction]
fn cli_main(argv: Vec<OsString>) -> i32
```

clap owns all CLI parsing: subcommands, `--help`, defaults, `choices`, error
messages, and (via `clap_complete`) shell completion. The Python console
scripts are thin forwarders:

```python
def main() -> int:
    from . import _core
    return _core.cli_main(sys.argv[1:])
```

There is no CLI parsing logic in Python — no argparse, no duplicated command
tree, no drift between two parsers.

### 2. Capabilities stay on the D09 wire protocol

Engine capabilities the CLI invokes (scaffold, validate, render, …) cross the
FFI boundary as versioned JSON envelopes through the shared
`qgis-protocol`/`qgis-engine` components, exactly as `qgis-py` and `qgis-node`
do (D09). The CLI transport does not wrap argv in a JSON envelope, and the
qgis-py protocol gains no namespaced CLI-invocation surface. There is also no
separate qgis-sdk protocol/engine pair: shared components are reused, and the
CLI behavior lives in the Rust CLI library (below).

### 3. Crate layout: one parser, two frontends, no pyo3 in the library

- `crates/qgis-sdk-core` is a new **pure-Rust library** holding the clap command
  tree and the plugin handlers, with `pub fn run_cli(argv) -> i32` as its entry
  point. It has no pyo3, no qgis-sys and no QGIS. It is not published (the plugin
  CLI is not a crates.io product), and it is a dependency only of `qgis-sdk`.
- The two Rust binaries are each a
  one-line `main` over `qgis_sdk_core::main_entry()`. `qgis-sdk` is an exact
  alias of the plugin CLI (D13 §1): same parser, same help, same exit codes, with
  no sibling-process delegation and no reduced reimplementation.
- `crates/qgis-sdk` depends on `qgis-sdk-core` and adds the `cli_main` pyfunction
  above. The Python extension and the Rust binaries share one parser.
- `qgis-cli` is **not** changed by this decision. It stays the GIS-execution CLI
  (D13 §1), so plugin tooling does not enter it. An earlier draft of this record
  put the command tree into `qgis-cli`; that conflicted with D13's rejected
  alternative "Put every SDK command in `qgis-cli`" and was corrected here.

### 4. Type stub beside the extension

`_core.pyi` is generated with `pyo3-stub-gen` and shipped beside the `.so`
inside the package, so `import qgis_sdk._core` type-checks and autocompletes.
The stub is for type checkers and IDEs; the runtime import works because
maturin places the extension inside the package (`module-name =
"qgis_sdk._core"`, `python-source = "src"`).

### 5. A missing extension is a loud CLI error

If `qgis_sdk._core` is not importable, the CLI prints an explicit error — the
command requires the native wheel; build it with `maturin develop` or install
the wheel — and exits non-zero. There is no silent `_fallback_cli.py`
re-implementation of command semantics on the CLI path (TASK-26 AC#3's
"deliberate native-extension-unavailable error with no alternate command
semantics"). The wheel always contains the `.so`, so the fallback only ever
existed for unbuilt source checkouts, which now fail at build time instead.
Pure-Python import-time fallbacks for *library* modules (for example the
Styles IR) are unaffected; this decision covers the CLI path only.

### 6. Edge cases are owned by the transport contract

- **Non-UTF-8 argv**: `cli_main` takes `Vec<OsString>` (falling back to lossy
  `String` only where clap requires it), so odd bytes in arguments survive the
  boundary.
- **Exit codes**: `cli_main` returns `i32`; Python maps it with `sys.exit`. No
  exception-to-exit-code translation layer.
- **stdout/stderr**: Rust prints in-process — the extension runs inside the
  Python process, so no piping or capture is needed.
- **`--help` and completion**: rendered by clap/`clap_complete` in Rust,
  identical for the binary and the Python entry point.
- **Tests**: call `_core.cli_main([...])` directly and assert exit code plus
  captured output; they exercise the real parser.

## Alternatives considered

- **JSON envelope around argv** (`invoke({"op": "cli", "argv": [...]})`,
  re-parsed by clap in the engine): rejected for the CLI transport. It adds a
  serialization layer around an in-process call, and extension and parser can
  never skew because the `.so` ships inside the wheel — there is no version to
  negotiate. It would also lose clap's help/completion UX at the Python entry
  point. Retained where it earns its keep: cross-package capability calls
  (D09).
- **Per-command typed pyfunctions** (the current `_core` shape —
  `scaffold_plugin`, `validate_plugin_structure`, …): rejected as the CLI
  transport. Python call sites would re-encode parsing knowledge (defaults,
  choices, aliases) and drift from clap. Kept only as engine-internal
  functions behind the wire protocol.
- **Keeping `_fallback_cli.py`**: rejected. It is the silent duplication
  TASK-26 names; a missing native extension must fail loudly, not behave
  differently.

## Consequences

- TASK-26 AC#1 is answered at the transport layer: Python is a thin argv
  client, Rust owns all command behavior, and capabilities reuse the shared
  qgis-protocol/qgis-engine components. The remaining engine-ownership detail
  (operation namespacing, payload/result/error shapes) is inherited from
  D09/D12 rather than redefined.
- TASK-26 AC#3's fallback policy is decided: a deliberate
  native-extension-unavailable error with no alternate command semantics.
- The CLI path never imports PyQGIS/PyQt (D13); QGIS-hosted plugin runtime
  stays outside the CLI boundary.
- Implementation is TASK-26 (Python thin client + fallback removal), TASK-41
  (the pure-Rust qgis-cli lib surface), and TASK-42 (stabilize the Python/Node
  FFI clients and CLI launchers).

## Related records

- [D09 — Wire Protocol over FFI](D09-wire-protocol-over-ffi.md) — the capability
  transport this decision keeps.
- [D13 — Rust CLI, FFI, and QGIS SDK product boundaries](D13-rust-cli-ffi-and-qgis-sdk-boundaries.md)
  — product boundaries; `qgis-sdk` stays an exact alias.
- [doc-7 — Rust CLI, Cross-Language FFI, and QGIS SDK Product Boundaries](../../backlog/docs/architecture/doc-7%20-%20Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md)
- [TASK-26 — Refactor qgis-sdk CLI onto the shared Rust engine wire protocol](../../backlog/tasks/task-26%20-%20Refactor-qgis-sdk-CLI-onto-the-shared-Rust-engine-wire-protocol.md)
- [TASK-40 — Define Rust CLI, FFI, and QGIS SDK product boundaries](../../backlog/tasks/task-40%20-%20Define-Rust-CLI-FFI-and-QGIS-SDK-product-boundaries.md)
- [TASK-41 — Build the pure-Rust qgis-cli capability surface](../../backlog/tasks/task-41%20-%20Build-the-pure-Rust-qgis-cli-capability-surface.md)
- [TASK-42 — Stabilize Python and Node FFI clients and CLI launchers](../../backlog/tasks/task-42%20-%20Stabilize-Python-and-Node-FFI-clients-and-CLI-launchers.md)
