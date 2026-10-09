# conda-forge recipe for qgis-py

This directory contains a conda-forge style recipe that builds the `qgis-py` Python package with its Rust extension. The package is a thin FFI API and ships no command-line interface.

The recipe lives at `py-packages/qgis-py/recipes/qgis-py/` while the Rust it compiles
lives at `py-packages/qgis-py/src-rust/`, so `source.path` points at the repository root
(`../../../..`) and the commands below all run from there.

## Build locally with conda-build

```bash
conda install -c conda-forge conda-build
conda build recipes/qgis-py/ -c conda-forge
```

## Build with pixi

```bash
pixi shell -e default
pixi run cargo build -p qgis-py --release
(cd py-packages/qgis-py && maturin build --release)
```

## Publish to conda-forge

1. Fork https://github.com/conda-forge/staged-recipes
2. Copy this recipe to `recipes/qgis-py/` in your fork
3. Open PR — conda-forge bots will build and test for Linux, macOS, Windows
4. Once merged, conda-forge will publish `qgis-py` and auto-update via bot

## Two variants

- **Pure-Rust (lightweight)**: No QGIS dependency. Supports extent, CRS and tile planning through the Python API. This is what `pip install qgis-py` gives you.
- **Full (with QGIS)**: Depends on `qgis >=3.44.9` from conda-forge. Adds rendering and project access, which the engine starts QGIS for in-process. To get this, `conda install -c conda-forge qgis qgis-py` or enable the `qgis` dependency in meta.yaml.

The recipe currently builds the lightweight variant by default, but you can uncomment the `qgis` dependency for full backend.
