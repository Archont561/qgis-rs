---
type: Tool
title: Pixi
description: "Pixi environment manager — conda-forge dependencies, tasks, and features."
status: stable
tags: [pixi, conda, environment, tooling]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
sources:
  - id: pixi-docs
    resource: https://pixi.sh
    title: "Pixi official documentation"
    author: team:prefix-dev
  - id: pixi-scipy2025
    resource: https://cfp.scipy.org/scipy2025/talk/GJACX9/
    title: "Reproducible Science Made Easy: Package Management with Pixi (SciPy 2025)"

---

# Pixi

## What Is Pixi?

[Pixi](https://pixi.sh) is a cross-platform, multi-language package manager built on the conda ecosystem by [prefix.dev](https://prefix.dev). It provides Cargo-like ergonomics for managing conda-forge and PyPI dependencies with automatic lockfiles.

For qgis-rs, pixi replaces manual conda/mamba environment setup and provides a unified task runner.

## Project Configuration (`pixi.toml`)

### Channels & Platform

```toml
[workspace]
name      = "qgis-rs"
channels  = ["conda-forge"]
platforms = ["linux-64"]
```

Currently Linux-only due to QGIS conda-forge availability.

### Dependencies

| Package        | Version        | Purpose                           |
|----------------|----------------|-----------------------------------|
| `rust`         | ≥1.96, <1.97  | Rust toolchain                    |
| `cxx-compiler` | ≥1.11, <2     | C++ compiler with CXX support     |
| `clang-tools`  | ≥22.1, <23    | clang-format + clang-tidy         |
| `lefthook`     | ≥2.1, <3      | Git hooks manager                 |
| `convco`       | ≥0.6, <0.7    | Conventional commit checker       |

### Feature: `qgis`

```toml
[feature.qgis.dependencies]
qgis = ">=3.44.9,<4"
```

The QGIS dependency is in a feature so that lightweight tasks (formatting, linting Rust code) don't require downloading the entire QGIS stack.

The `default` environment activates the `qgis` feature.

## Tasks

### Formatting
- `fmt-rs` — `cargo fmt --all`
- `fmt-cpp` — `clang-format -i` on all `.cpp` and `.h` files
- `fmt` — runs both

### Linting
- `lint-rs` — `cargo clippy --workspace --all-targets -- -D warnings`
- `lint-cpp` — `clang-tidy` with sysroot, Qt, and QGIS includes (depends on `_build-for-lint`)
- `lint` — runs both

### Testing
- `test` — basic tests (`application_info`), with optional `--clean` flag
- `test-full` — full tests including `application_lifecycle` and `vector_layer`

Both set:
- `QT_QPA_PLATFORM=offscreen` — prevents Qt display requirement
- `PROJ_DATA=$CONDA_PREFIX/share/proj` — PROJ data location
- `QGIS_PLUGINPATH=$CONDA_PREFIX/lib/qgis/plugins` — provider plugins

### Internal
- `setup` — creates a symlink: `libqca-qt5.so.2` → `libqca-qt6.so.2`
- `_build-for-lint` — builds qgis-sys so clang-tidy can find generated headers

### Scaffolding
- `scaffold <layer> <concept> <qgis_class> <short_name>` — generates new FFI boilerplate

### CI
- `ci` — `check-rs` + `check-cpp` + `lint-rs` + `test`
- `ci-full` — `ci` + `lint-cpp` + `test-full`

## Common Commands

```bash
pixi shell                  # enter the environment
pixi run fmt                # format everything
pixi run lint               # lint everything
pixi run test               # run basic tests
pixi run test-full          # run all tests
pixi run scaffold core raster QgsRasterLayer raster
```

## Offline / Sandbox Bootstrapping

When pixi is not available (e.g., sandboxed CI, restricted network environments),
the qgis-rs environment can be bootstrapped from a pre-built **pixi-sandbox pack**:

```bash
# Option A: automated
sh scripts/setup-env.sh
. scripts/use-pack.sh

# Option B: manual clone
git clone --depth 1 --branch env/qgis-rs-linux-64 \
  https://github.com/Archont561/qgis-rs pack
cd pack && bash ./pixi-sandbox-*.sh
. scripts/use-pack.sh
```

This provides cargo, rustc, clang-tools, QGIS headers/libraries, and pixi itself
without needing conda-forge or prefix.dev. See [env-provisioning.md](/env-provisioning.md)
for the full design and receipt format.

The `env.yml` GitHub Actions workflow automatically rebuilds and republishes
the pack whenever `pixi.toml` or `pixi.lock` changes on `main`.
