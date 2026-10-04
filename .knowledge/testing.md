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

SDK-specific pure-Python and QGIS-hosted test separation is tracked by [TASK-1](../backlog/tasks/task-1%20-%20Make%20the%20full%20QGIS%20SDK%20test%20suite%20headless%20and%20CI-green.md), [TASK-2](../backlog/tasks/task-2%20-%20Add%20a%20dedicated%20QGIS%20SDK%20integration%20test%20runner%20and%20CI%20job.md), and [TASK-4](../backlog/tasks/task-4%20-%20Cover%20real%20QGIS%20network%20and%20task-manager%20integration.md). Property and fixture migration is [TASK-23](../backlog/tasks/task-23%20-%20Refactor-every-test-suite-onto-property-based-and-fixture-driven-testing.md).

### QGIS SDK runtime matrix

The SDK suite is intentionally runnable in two modes:

- **Pure Python:** run `python -m pytest tests -v` from a Python environment that does not provide `qgis.core` or Qt. Tests marked `pure_python` run; tests marked `qgis` are skipped before their bodies import QGIS. Fake interfaces, network managers, task managers, dialogs, and WebEngine objects cover the host-independent API.
- **QGIS/offscreen:** run `pixi run -e default setup` once, then
  `pixi run -e default env QGIS_REQUIRE_NATIVE=1 python -m pytest py-packages/qgis-sdk/tests -v`.
  `QT_QPA_PLATFORM=offscreen` is set before the SDK is imported. The reusable
  `qgis_environment`, `qgis_available`, `pure_python`, and `qgis_app` fixtures
  describe the runtime; `qgis_app` only returns a live host-owned
  `QgsApplication` and otherwise skips safely. The committed simple-plugin
  integration test starts its own subprocess so native startup and teardown
  cannot corrupt the main pytest process.

The package registers `qgis_sdk.testing` through its `pytest11` entry point;
`tests/conftest.py` also registers the same plugin only when that entry point is
not present, so source checkouts and installed environments behave identically.
Do not create a `QApplication` or `QgsApplication` in a normal unit test;
use the fakes for pure-Python tests and the subprocess/host fixtures for native
coverage. This keeps modal dialogs and QGIS singletons out of pytest teardown.

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
