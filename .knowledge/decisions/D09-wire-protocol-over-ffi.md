---
type: Decision
id: D09
title: A Versioned Wire Protocol Across the FFI Boundary
description: "One `invoke(json) -> json` function per binding instead of a hand-mirrored PyO3/NAPI class surface."
status: accepted
tags: [ffi, pyo3, napi, protocol, engine, architecture]
date: 2026-10-03T00:00:00Z
---

# D09: A Versioned Wire Protocol Across the FFI Boundary

> The native QGIS manager extension of this decision is recorded in
> [D12 — QGIS Native Manager over the C ABI](D12-qgis-native-manager-over-c-abi.md).
> D09 remains the protocol decision; D12 fixes the owner-thread, schema,
> artifact, crash-isolation, and RFC 19 naming rules for the C++ consumer.

## The Question

`qgis-rs` ships the same capability to three audiences: Rust callers, Python
(`qgis_py`, via PyO3) and Node (`qgis-rs`, via NAPI). How much of the API should
cross each FFI boundary?

The answer we had was **all of it**. `crates/qgis-py` defined `PyExtent`,
`PyCrs`, `PyTile`, `PyTilePlan`, `PyZoomRange`, `PyProject`…; `crates/qgis-node`
defined `ExtentWrapper`, `CrsWrapper`, `TilePlanWrapper`… Every domain type
existed three times, every new method had to be written three times, and the
two binding crates were each several hundred lines of code whose only job was
re-typing a signature that already existed in `qgis-render`.

## The Decision

**Each binding crate exposes exactly one function:**

```rust
// crates/qgis-py/src/lib.rs  (and the NAPI twin)
#[pyfunction]
fn invoke(request: &str) -> String { qgis_engine::invoke(request) }
```

Everything else is the **wire protocol** in `crates/qgis-protocol`:

```jsonc
// request
{ "transport_version": 1, "operation": "plan_tiles", "payload": { … } }
// response
{ "transport_version": 1, "ok": true,  "result": { … } }
{ "transport_version": 1, "ok": false, "result": { "kind": "invalid_extent", "error": "…" } }
```

* `TRANSPORT_VERSION: u32 = 1` is stated once, in `qgis-protocol`, and echoed in
  every response. A client built against a transport the engine does not speak
  gets `unsupported_transport` with `{supported, received}` — not a segfault,
  not silence.
* `Operation` is a **closed enum**, and `Operation::all()` is what
  `engine_info` reports. The set of things the engine can do is therefore a
  compile-time fact, discoverable at runtime.
* `crates/qgis-engine` owns `invoke(&str) -> String`: parse, match one arm per
  operation, serialise. It restates no rule that `qgis-render` already owns.
* The ergonomic API — `Extent`, `Crs`, `TilePlan`, `Project` — is written **in
  each host language**, in Python and in JavaScript, over that one call.

Everything on the wire is `snake_case`, including operation names. The
JavaScript client renames to camelCase at its own edge, where its users expect
it; Python uses the wire names as they are.

## Why

**A binding is not an API; it is a translation of one.** Mirroring the types
means the Python surface and the Node surface drift apart the first time
someone adds a method to only one of them — and nothing fails, because nothing
compares them. With one function, there is nothing to drift: both clients are
exercised against the same JSON, and the golden values (4568 tiles for
`14,50,15,51` at z10-14; `tile_from_lon_lat(10, 13.9, 51.1) → {10, 551, 342}`)
are asserted in all three test suites.

**The boundary becomes testable without the boundary.**
`cargo test -p qgis-engine` covers every operation at exactly the JSON level the
bindings see, with no Python interpreter and no Node process in the loop. A
failure there is a failure of the thing itself, not of the harness.

**Adding an operation is one arm, not three classes.** Add the variant to
`Operation`, the payload struct, the match arm, and the two clients can reach it
*immediately* through their escape hatch (`qgis_py.invoke(...)`,
`require("qgis-rs").invoke(...)`) — the typed sugar can follow later, or never,
for operations only a script needs.

**Versioning becomes possible.** A published wheel and a published addon have
independent release cadences from the engine they load. An explicit
`transport_version` is the only thing that turns "mismatched build" from
undefined behaviour into an error message.

## The Costs, Accepted

* **A serialise/parse pair per call.** Measured on this repository's own
  values: `new Extent("14,50,15,51")` ≈ 4µs, a z10-14 plan with per-level counts
  ≈ 18µs, and the same plan with all 4568 tiles materialised ≈ 3.5ms. The cost
  is real and it is *proportional to the payload*, which is why `plan_tiles`
  counts by default and enumerates only on `include_tiles: true`. For anything
  per-feature or per-pixel, the answer is not a smaller envelope — it is to do
  the loop inside one operation.
* **No static types across the boundary.** The host-language clients are the
  typed layer (`index.d.ts`, `_api.py`), and they are tested against the real
  addon, not a mock.
* **A breaking change for existing users.** Taken deliberately: `PyExtent` and
  `ExtentWrapper` are gone rather than kept as a deprecated shadow surface, and
  the pure-Python / pure-JS fallbacks are gone with them — a fallback is a
  second implementation of the maths, which is a second set of answers.

## Alternatives Considered

| Alternative | Why not |
| --- | --- |
| Keep the mirrored class surface | Three implementations of one API, drifting silently; most of the diff in any feature PR was mechanical re-typing |
| Mirror, but generate the mirrors | A code generator is a second toolchain and a second debugging story to keep an interface we did not want |
| An out-of-process engine (socket, stdio) | Pays a process boundary for something that is already in the address space; the in-process call is 4µs, not 4ms |
| Keep fallbacks for `_core`-less installs | The fallback *is* a different implementation; a quietly wrong answer is worse than an ImportError |

## Consequences

* `crates/qgis-protocol` and `crates/qgis-engine` exist and are published.
* `crates/qgis-py` is ~65 lines, `crates/qgis-node` ~40.
* `py-packages/qgis-py/python/qgis_py/{_transport,_api}.py` and
  `ts-packages/qgis-node/index.js` are the ergonomic APIs, each tested as a
  boundary client against a real build.
* `_fallback.py`, `__init__.pyi` and `fallback.js` are deleted.
* The escape hatch is public and documented: an operation a client has no class
  for is still reachable, which is what keeps a newer engine usable from an
  older package.
