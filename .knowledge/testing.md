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

### Basic Tests (`pixi run test`)

Run without full QGIS initialization:
- `application_info` — verifies version, Qt version, and platform strings

### Full Tests (`pixi run test-full`)

Require `QgsApplication::initQgis()`:
- `application_lifecycle` — tests init/exit round-trip with info retrieval
- `vector_layer` — tests layer creation, validity, metadata access

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
