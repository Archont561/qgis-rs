# conda-forge recipe for qgis-rs

This directory contains a conda-forge style recipe that builds the `qgis-rs` Python package with Rust extension and `qgis-cli` binary.

The recipe lives at `py-packages/qgis-rs/conda-recipe/` while the Rust it compiles
lives at `crates/qgis-py/`, so `source.path` points at the repository root
(`../../..`) and the commands below all run from there.

## Build locally with conda-build

```bash
conda install -c conda-forge conda-build
conda build conda-recipe/ -c conda-forge
```

## Build with pixi

```bash
pixi shell -e default
pixi run cargo build -p qgis-py --release
(cd py-packages/qgis-rs && maturin build --release)
```

## Publish to conda-forge

1. Fork https://github.com/conda-forge/staged-recipes
2. Copy this recipe to `recipes/qgis-rs/` in your fork
3. Open PR — conda-forge bots will build and test for Linux, macOS, Windows
4. Once merged, conda-forge will publish `qgis-rs` and auto-update via bot

## Two variants

- **Pure-Rust (lightweight)**: No QGIS dependency. Supports `info`, `tiles --dry-run`, `version`, tile planning via Python API. This is what `pip install qgis-rs` gives you.
- **Full (with QGIS)**: Depends on `qgis >=3.44.9` from conda-forge. Supports `render`, `tiles` (actual rendering), `export`, `serve`. To get this, `conda install -c conda-forge qgis qgis-rs` or enable the `qgis` dependency in meta.yaml.

The recipe currently builds the lightweight variant by default, but you can uncomment the `qgis` dependency for full backend.
