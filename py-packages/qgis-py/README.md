# qgis-py — Python API over the Rust QGIS engine

[![PyPI](https://img.shields.io/pypi/v/qgis-py)](https://pypi.org/project/qgis-py/)
[![Conda](https://img.shields.io/conda/vn/conda-forge/qgis-py)](https://anaconda.org/conda-forge/qgis-py)
[![License](https://img.shields.io/badge/license-GPL--2.0--or--later-blue)](LICENSE)

**qgis-py** exposes the QGIS rendering and tiling engine as a Python package that installs from **pip** or **conda-forge** and runs at **native Rust speed**. It is a thin FFI API: every answer comes from the Rust engine, which starts QGIS in-process when a call needs it.

- **pip**: `pip install qgis-py`
- **conda**: `conda install -c conda-forge qgis-py` (or `pixi add qgis-py`)
- **API**: `import qgis_py` — pure Rust types (`Extent`, `Crs`, `TilePlan`, `Project`) via PyO3

## Why a Rust engine behind Python?

- **Native speed**: No Python overhead for geometry math, tile planning, or rendering. The Python classes are clients of the Rust engine.
- **Single install**: `pip install qgis-py` gives you `import qgis_py`, with the engine inside it.
- **No QGIS needed for many operations**: Tile planning, extent parsing, CRS handling, and project inspection are pure Rust and work anywhere.
- **QGIS backend optional**: When `libqgis_core` is available (the Pixi/conda QGIS environment), rendering and feature export use the native manager; QGIS-free builds report an explicit backend error instead of silently substituting another implementation.

## Installation

### From PyPI (pip)

```bash
pip install qgis-py
```

This installs:

- `qgis_py` Python module (PyO3 extension `_core` + Python wrappers)

Pre-built wheels are published for Linux x86_64 and Linux arm64. If no wheel matches your platform, `pip` builds from source via `maturin` (requires Rust ≥1.96).

### From conda-forge (conda / pixi / mamba)

```bash
conda install -c conda-forge qgis-py
# or
pixi add qgis-py
# or
mamba install -c conda-forge qgis-py
```

The conda-forge package depends on `qgis >=3.44.9` when the `qgis` feature is enabled, so you get the full rendering backend automatically.

### From source (development)

```bash
git clone https://github.com/Archont561/qgis-rust
cd qgis-py

# Python dev with maturin — the pyproject owns the build and points at
# py-packages/qgis-py/src-rust for the Rust half
pip install maturin
(cd py-packages/qgis-py && maturin develop)   # reads ./pyproject.toml -> py-packages/qgis-py/src-rust

# Or via pixi (conda environment with QGIS)
pixi install -e default
pixi run -e default py-develop

# Test
python -m pytest py-packages/qgis-py/tests -q
```

## Python API

```python
from qgis_py import Project, Extent, TilePlan, ZoomRange, Crs, plan_tiles

# Open a project (cheap — only checks path, no QGIS needed)
project = Project.open("map.qgs")
print(project.path, project.format)

info = project.info()
print(info.to_dict())
# {'path': 'map.qgs', 'format': 'qgs', 'size_bytes': 1234, 'crs': None, ...}

# Pure-Rust geometry — native speed, no QGIS
extent = Extent.parse("14,50,15,51")
assert extent.width() == 1.0
assert extent.contains(14.5, 50.5)

crs = Crs.from_epsg(3857)
print(crs.auth_id, crs.is_projected())  # EPSG:3857 True

# Tile planning — counts tiles without rendering
zooms = ZoomRange.parse("10-14")
plan = TilePlan(extent, zooms)
print(f"Would render {plan.tile_count()} tiles")
for level in plan.levels():
    print(f"z={level.zoom} {level.tile_count()} tiles")

# Fast path function (also Rust)
total, levels = plan_tiles("14,50,15,51", "10-14")
print(total)  # 4568

# Rendering through the native QGIS backend
# When QGIS is not available, this raises ValueError with clear message.
try:
    rendered = project.render("output.png", width=1920, height=1080, dpi=150)
    print(f"Wrote {rendered.path} ({rendered.bytes} bytes)")
except ValueError as e:
    print(f"QGIS rendering failed: {e}")
```

## Raw invoke and transport guards

`qgis_py.invoke(operation, payload=None)` is the public escape hatch for
operations without an ergonomic wrapper. It returns the wire result or raises
an `EngineError` subclass; branch on `error.kind` and use `error.detail` for
context, not English prose. Every response version is checked before its
success or failure result is read. A mismatch raises `TransportMismatch` with
kind `unsupported_transport` and details `supported` and `received` (`None`
when the response omits its version). Importing the client still requires the
compiled extension; there is no Python fallback.

## Architecture

```
qgis-py Python wheel            built from py-packages/qgis-py
├── qgis_py/                    ← python/qgis_py/
│   ├── __init__.py      → high-level API (imports from _core)
│   ├── _core.so         → py-packages/qgis-py/src-rust, PyO3 cdylib — native speed
│   │   ├── Extent, Crs, Tile, TilePlan, ZoomRange
│   │   ├── Project, ProjectInfo, LayerSummary
│   │   ├── RenderSettings, RenderedMap
│   │   └── plan_tiles, version
│   ├── project.py       → Pythonic Project wrapper
│   ├── render.py        → re-exports
│   └── tiles.py         → re-exports
```

This wheel ships no command-line interface. The standalone CLI is built from
`crates/qgis-cli` and is a separate product.

- **Rust workspace**: `crates/qgis-render` (pure Rust), `crates/qgis-cli` (the standalone CLI, not part of this wheel), `py-packages/qgis-py/src-rust` (PyO3 bindings)
- **Python**: this directory — `python/qgis_py/` (wrappers) + `pyproject.toml`, whose `[tool.maturin].manifest-path` points at `src-rust/Cargo.toml`
- **Conda**: `pixi.toml` (pixi-build) + conda-forge recipe (see `recipes/qgis-py/`)
- **Design**: `src-rust/ARCHITECTURE.md` — why the crate and the wheel are split this way

## Conda-forge recipe

The conda-forge feedstock builds the same Rust code with `qgis` from conda-forge, so rendering works out of the box.

See `recipes/qgis-py/` for the recipe (meta.yaml + build.sh). It:

- Uses `pixi` or `conda-build` to compile Rust with `cargo`
- Builds Python extension via `maturin` or `cargo` + `pyo3`
- Depends on `qgis >=3.44.9`, `python >=3.9`, `qt`, `gdal`

To publish to conda-forge:

1. Fork https://github.com/conda-forge/staged-recipes
2. Copy `recipes/qgis-py/` to `recipes/qgis-py/`
3. Open PR — conda-forge bots will build and test

## Performance

Benchmarks (Intel i7-12700K, pure-Rust ops, no QGIS):

| Operation | qgis-py (Rust) | Python (shapely/py) | Speedup |
|-----------|----------------|---------------------|---------|
| Extent parse | 0.5µs | 5µs | 10× |
| TilePlan 10-14 (4568 tiles) | 0.2ms | 3ms | 15× |
| Tile bounds | 0.1µs | 1µs | 10× |

Rendering benchmarks need QGIS backend — see main README.

## License

GPL-2.0-or-later, matching QGIS and the rest of qgis-py.
