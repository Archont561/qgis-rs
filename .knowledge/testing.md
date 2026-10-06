---
type: Practice
title: Testing
description: Test structure, fixtures, environment variables, and QT_QPA_PLATFORM requirements.
status: stable
tags: [testing, integration, fixtures, qt]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# Testing

## Test Types

### Rust and QGIS tests

Repository-wide gates are owned by `crates/xtask` ([D10](decisions/D10-xtask-over-shell-scripts.md)):

- `pixi run gates` — Rust, C++, package, and non-coverage checks.
- `pixi run -- cargo nextest run -p qgis-mcp --no-default-features` — QGIS-free
  capability reporting and backend-unavailable behavior.
- `pixi run -- cargo nextest run -p qgis-engine --no-default-features` — QGIS-free
  native operation errors.
- `pixi run -- cargo nextest run -p qgis-sys --no-default-features` — QGIS-free
  manager adapter build.
- `pixi run -- cargo nextest run -p qgis-sys --features qgis-sys/qgis -E 'binary(/native_manager/)' --test-threads=1` —
  native-manager lifecycle, dispatch, layer coverage and owner-thread shutdown.
  The `qgis` feature is not optional here: without it these suites are compiled
  out and nextest answers `no tests to run` rather than passing vacuously.
- `pixi run -- cargo test --workspace --no-default-features --doc` — the crate-level
  doc examples, which nextest does not run.

The runner is **cargo-nextest** (declared in `pixi.toml`, carried in the offline pack):
one process per test, so a Qt abort names the test that caused it instead of killing
its whole binary, and the report is one line per test. `cargo test` remains the way to
run doctests, and only that.

The old `pixi run test` and `pixi run test-full` names are historical and are not current root tasks.

### Running only what a change can break

`pixi run gates` is the pre-push gate, not the inner loop. While working, run the narrowest thing
that can still go red:

- `pixi run -- cargo nextest run -p <crate>` — one crate.
- `pixi run -- cargo nextest run -E 'rdeps(<crate>)'` — that crate **and every crate that depends on
  it**; nextest's filter expressions read the Cargo graph, which is as close to "affected tests" as
  this repository gets. `rdeps(qgis-protocol)` is 130 tests against the workspace's 247.
- `pixi run -- cargo nextest run -E 'test(<substring>)'` — by test name, across the workspace.
- `pixi run -e default python -m pytest <file> -q` / `-k <substring>` — one Python file or test.
- `pixi run -- bun test <file>` — one TypeScript file.
- `pixi run -- bun x turbo run test --filter='...[HEAD^1]'` — every package downstream of the last
  commit. Note that all Rust crates are one turbo package (`@qgis/rust`), so inside `crates/` this
  selects the whole workspace and `-p`/`-E` is the finer tool. On an offline machine add
  `CARGO_NET_OFFLINE=true --env-mode=loose`, or the NAPI build reaches for crates.io.

Turbo caches test results, so an unchanged package replays instead of re-running; `--force` defeats
that and belongs in measurements, not in the loop.

For a single entry point over those rules, run `pixi run xtask affected`. It compares committed
changes with the merge base of `origin/main` and also includes staged, unstaged, deleted, renamed,
and untracked files. Rust paths become nextest `rdeps(<crate>)` selections; Python, TypeScript, and
docs paths become downstream Turbo package filters. Use `--dry-run` to inspect the deterministic
plan, `--base <ref>` to compare with another base, and `--force` only when measuring without
Turbo's cache. Root manifests and lockfiles, shared fixtures, workflow files, scripts, and xtask's
own gate automation deliberately fall back to `pixi run gates`; an unknown top-level path does the
same. This is an inner-loop accelerator, not a replacement for the full pre-push gate.

SDK-specific pure-Python and QGIS-hosted test separation is tracked by [TASK-1](../backlog/tasks/task-1%20-%20Make%20the%20full%20QGIS%20SDK%20test%20suite%20headless%20and%20CI-green.md), [TASK-2](../backlog/tasks/task-2%20-%20Add%20a%20dedicated%20QGIS%20SDK%20integration%20test%20runner%20and%20CI%20job.md), and [TASK-4](../backlog/tasks/task-4%20-%20Cover%20real%20QGIS%20network%20and%20task-manager%20integration.md). Property and fixture migration is [TASK-23](../backlog/tasks/task-23%20-%20Refactor-every-test-suite-onto-property-based-and-fixture-driven-testing.md).

### The six test commands (TASK-35)

Six things get tested, and they do not all need the same machine. Each has one
command, and the layer gates are **strict**: a gate whose layer is missing
fails rather than skipping, because a gate that skipped has proved nothing.
`QGIS_TEST_LAYER` narrows the run to one layer and turns the permissive
skip-what-you-cannot-reach policy off.

| What | Command | Needs |
| --- | --- | --- |
| **Pure** — no Qt, no QGIS, no WebEngine | `pixi run -- bun --filter=qgis-sdk-py run test:pure` | nothing |
| **Fake-host** — the fakes and `BridgeHarness`, host behaviour without a host | included in the pure gate (the fakes import no Qt) | nothing |
| **Qt** — real widgets, offscreen | `pixi run -- bun --filter=qgis-sdk-py run test:qt` | PyQt5 |
| **QGIS** — a real `QgsApplication`, serialized | `pixi run -- bun --filter=qgis-sdk-py run test:qgis` | `qgis.core` |
| **WebEngine** — optional, off the default path | `pixi run -- bun --filter=qgis-sdk-py run test:webengine` | `PyQt5.QtWebEngineWidgets` |
| **Cross-language contract** — the shared `test-fixtures/bridge` vectors in Rust, Python and TypeScript | `pixi run xtask validate-bridge-fixtures` then `pixi run gates` | nothing |

`pixi run -- bun --filter=qgis-sdk-py run test` remains the permissive
whole-suite run and is the only one turbo fans out, so WebEngine never becomes
a dependency of ordinary bridge tests. The selection policy is pure data in
`qgis_sdk.testing.gates` and tested in `tests/test_layer_gates.py`; the gates
overlap on purpose (a test marked both `qt` and `webengine` runs in both) but
never leave a test in no gate at all, which is why `pure` is defined by the
*absence* of a layer marker rather than the presence of `pure_python`.

### QGIS SDK runtime matrix

The SDK suite is intentionally runnable in two modes:

- **Pure Python:** run `python -m pytest tests -v` from a Python environment that does not provide `qgis.core` or Qt. Tests marked `pure_python` run; tests marked `qgis` are skipped before their bodies import QGIS. Fake interfaces, network managers, task managers, dialogs, and WebEngine objects cover the host-independent API.
- **QGIS/offscreen:** run `pixi run -e default setup` once, then
  `pixi run -e default env QGIS_REQUIRE_NATIVE=1 python -m pytest py-packages/qgis-sdk/tests -v`.
  `QT_QPA_PLATFORM=offscreen` is set before the SDK is imported. The reusable
  `qgis_environment`, `qgis_available`, `pure_python`, and `qgis_app` fixtures
  describe the runtime. `qgis_app` resolves in three steps: adopt the host's
  live `QgsApplication` when there is one, otherwise construct one through the
  `qgis_runtime` fixture **when the `qgis` gate is active**, otherwise skip.
  Only the middle case creates a native application, and only because the gate
  asserted the layer exists; `qgis_sdk.testing.qgis_lifecycle` owns that
  lifecycle and calls `exitQgis()` before interpreter teardown, which is what
  the "aborts during pytest shutdown" folklore was really about. The committed
  simple-plugin integration test starts its own subprocess so native startup
  and teardown cannot corrupt the main pytest process.

The package registers `qgis_sdk.testing` through its `pytest11` entry point;
`tests/conftest.py` also registers the same plugin only when that entry point is
not present, so source checkouts and installed environments behave identically.
Do not create a `QApplication` or `QgsApplication` in a normal unit test;
use the fakes for pure-Python tests and the subprocess/host fixtures for native
coverage. This keeps modal dialogs and QGIS singletons out of pytest teardown.

### `qgis_sdk.testing` is a package, one module per concern (TASK-32)

`qgis_sdk/testing.py` became `qgis_sdk/testing/` in the layout
[doc-5](../backlog/docs/testing/doc-5%20-%20QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md)
specifies — `environment`, `calls`, `iface`, `ui`, `bridge`, `qgis_api`,
`network`, `tasks`, `processing`, `data`, `strategies`, `plugin` — with
`__init__.py` as the compatibility facade. Every pre-split name and every
fixture name still resolves through `qgis_sdk.testing`, and
`tests/test_testing_layers.py` holds the frozen list that says so.

Four things are new rather than moved:

- **`Call`/`CallLog`** — one shape for every recorded call (`target`, dotted
  `method`, keyword `args`). Each fake owns one and accepts one, so handing
  several fakes `calls=shared_calls` makes cross-fake ordering assertable. The
  old per-fake lists (`iface.messages`, `manager.requests`) are untouched.
- **`FakeNetworkTransport`** — scripted replies keyed by `(method, url)`, with
  `reply`, `reply_sequence`, `fail`, `delay` (virtual seconds, nothing sleeps),
  `redirect` and request history. An unscripted route **raises**
  `NoScriptedReply`; the older `FakeNetworkManager` keeps its permissive
  `{"mock": true}` default because existing suites rely on it.
- **`FakeTaskManager.submit`/`run_next`/`chain`/`group`** — the explicit
  `PENDING → RUNNING → SUCCESS|FAILURE|CANCELED` machine, with `auto_run=False`
  for tests that need to decide when work happens. The celery-shaped
  `FakeTask`/`add_task` surface keeps celery's `STARTED`/`REVOKED` spellings;
  `canonical_state()` maps between the two vocabularies.
- **`BridgeHarness`** — a real router over the shared manifests in
  `test-fixtures/bridge/`: envelope, version, target, method, permissions, then
  arguments, in the order `crates/qgis-protocol`'s `validate_request` uses. The
  same malformed vectors are replayed through it in
  `tests/test_testing_bridge.py`, so the Python host and the Rust validator are
  proven to refuse the same input for the same reason — without sharing code.

`qgis_sdk.testing.strategies` holds the Hypothesis strategies (extents, zoom
ranges, CRS auth ids, plugin names, field specs, bridge requests/responses,
network responses, task transition paths). They generate **pure data only**;
the facade imports the module defensively so the SDK still imports where
`hypothesis` is absent.

Markers are now `qgis`, `qt`, `webengine`, `pure_python`, `network`, `tasks`,
and the collection hook skips a marked test **before its body runs** when the
layer is unreachable — `QgisTestEnvironment.layers` is what it reads. No module
under `qgis_sdk/testing/` imports PyQt or PyQGIS at module scope, which is
asserted from the source rather than from a lucky process.

## Environment Requirements

| Variable                    | Value                                    | Why                        |
|-----------------------------|------------------------------------------|----------------------------|
| `QT_QPA_PLATFORM`           | `offscreen`                              | Prevents Qt from opening a display |
| `PROJ_DATA`                 | `$CONDA_PREFIX/share/proj`               | CRS transformation data    |
| `QGIS_PLUGINPATH`           | `$CONDA_PREFIX/lib/qgis/plugins`         | Provider plugin discovery  |

The `setup` task creates a workaround symlink:
```bash
ln -sf $CONDA_PREFIX/lib/libqca-qt6.so.2 $CONDA_PREFIX/lib/libqca-qt5.so.2
```

## Single-Threaded Execution

All tests run with `--test-threads=1` because:
1. `QApplication` is a process-wide singleton — only one can exist
2. QGIS provider registries use global state
3. Some Qt subsystems are not thread-safe during initialization

## Test Helpers (`tests/helpers/mod.rs`)

`AppHandle` provides RAII-style application lifecycle management:

```rust
let _app = helpers::AppHandle::new();  // initQgis() on creation
// ... run tests ...
// exitQgis() called automatically on drop
```

## Fixtures

| File                      | Format      | Contents                          |
|---------------------------|-------------|-----------------------------------|
| `tests/fixtures/points.gpkg` | GeoPackage | 3 point features, EPSG:4326, fields: name |

## Running Specific Tests

```bash
# Single test file
pixi run test qgis-sys

# Clean build + test
pixi run test "" --clean
pixi run test qgis-sys --clean

# Full suite
pixi run test-full
```

## Adding New Tests

1. Create `tests/<name>.rs`
2. Add `mod helpers;` and use `AppHandle::new()` if QGIS is needed
3. Add the test name to the `test` or `test-full` task in `pixi.toml`
4. All tests in a file share the same `AppHandle` instance
