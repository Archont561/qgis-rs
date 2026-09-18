# qgis-rs — Python package with Rust-native CLI and API

[![PyPI](https://img.shields.io/pypi/v/qgis-rs)](https://pypi.org/project/qgis-rs/)
[![Conda](https://img.shields.io/conda/vn/conda-forge/qgis-rs)](https://anaconda.org/conda-forge/qgis-rs)
[![License](https://img.shields.io/badge/license-GPL--2.0--or--later-blue)](LICENSE)

**qgis-rs** exposes the QGIS rendering and tiling engine as a Python package that installs from **pip** or **conda-forge** and runs at **native Rust speed** — both the Python API and the `qgis-cli` command.

- **pip**: `pip install qgis-rs`
- **conda**: `conda install -c conda-forge qgis-rs` (or `pixi add qgis-rs`)
- **API**: `import qgis_rs` — pure Rust types (`Extent`, `Crs`, `TilePlan`, `Project`) via PyO3
- **CLI**: `qgis-cli` binary (Rust) + `qgis-cli` Python console script (same native code)

## Why a Rust binary inside a Python package?

- **Native speed**: No Python overhead for geometry math, tile planning, or rendering. The `qgis-cli` binary is a statically-linked Rust executable built with `cargo`.
- **Single install**: `pip install qgis-rs` gives you both `import qgis_rs` and `qgis-cli` on PATH.
- **No QGIS needed for many operations**: Tile planning (`tiles --dry-run`), extent parsing, CRS handling, and project inspection are pure Rust and work anywhere.
- **QGIS backend optional**: When `libqgis_core` is available (conda-forge `qgis` package), rendering and feature export use it; otherwise they report `Unimplemented` with a clear message, so CLI tooling can be developed without QGIS.

## Installation

### From PyPI (pip)

```bash
pip install qgis-rs
```

This installs:

- `qgis_rs` Python module (PyO3 extension `_core` + Python wrappers)
- `qgis-cli` executable (Rust binary built by maturin)
- `qgis-cli` and `qgis-rs` console scripts (`python -m qgis_rs.cli`)

Pre-built wheels are published for Linux x86_64, macOS (arm64 + x86_64), and Windows x86_64. If no wheel matches your platform, `pip` builds from source via `maturin` (requires Rust ≥1.96).

### From conda-forge (conda / pixi / mamba)

```bash
conda install -c conda-forge qgis-rs
# or
pixi add qgis-rs
# or
mamba install -c conda-forge qgis-rs
```

The conda-forge package depends on `qgis >=3.44.9` when the `qgis` feature is enabled, so you get the full rendering backend automatically. The `qgis-cli` binary is included in `$CONDA_PREFIX/bin`.

### From source (development)

```bash
git clone https://github.com/Archont561/qgis-rs
cd qgis-rs

# Python dev with maturin
pip install maturin
maturin develop --manifest-path packages/qgis-rs/Cargo.toml

# Or via pixi (conda environment with QGIS)
pixi install -e sdk
pixi run -e sdk maturin develop --manifest-path packages/qgis-rs/Cargo.toml

# Test
python -m pytest packages/qgis-rs/tests -q
qgis-cli --help
qgis-cli info map.qgs --json
qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 --dry-run
```

## Python API

```python
from qgis_rs import Project, Extent, TilePlan, ZoomRange, Crs, plan_tiles

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

# Rendering (needs QGIS backend — via conda-forge qgis package)
# When QGIS is not available, this raises ValueError with clear message.
try:
    rendered = project.render("output.png", width=1920, height=1080, dpi=150)
    print(f"Wrote {rendered.path} ({rendered.bytes} bytes)")
except ValueError as e:
    print(f"Rendering needs QGIS backend: {e}")
```

## CLI

The same Rust code powers both the standalone binary and the Python wrapper.

```bash
# Installed via pip or conda — binary on PATH
qgis-cli --help
qgis-cli version
qgis-cli info map.qgs
qgis-cli info map.qgs --json
qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 -o ./tiles/ --dry-run
qgis-cli render map.qgs -o map.png --width 1920 --height 1080 --dpi 150

# Via Python module (same speed — uses Rust extension directly)
python -m qgis_rs.cli info map.qgs --json
python -m qgis_rs.cli tiles map.qgs -z 10-14 -b 14,50,15,51 --dry-run
qgis-rs info map.qgs  # alias

# From Python API
from qgis_rs.cli import main
main(["info", "map.qgs", "--json"])
```

### Commands

| Command | Pure Rust? | Needs QGIS? | Description |
|---------|------------|-------------|-------------|
| `info` | ✅ | No (basic), Yes (layers, CRS) | Describe a project |
| `tiles --dry-run` | ✅ | No | Count tiles without rendering |
| `tiles` | ✅ | Yes | Render tile pyramid |
| `render` | ✅ | Yes | Render project to image |
| `export` | ✅ | Yes | Export layer features |
| `serve` | ✅ | Yes | HTTP server (WMS/WFS/XYZ) |
| `mcp` | ✅ | Partial | Model Context Protocol server |
| `version` | ✅ | No | Print version |

## Architecture

```
qgis-rs Python wheel
├── qgis_rs/
│   ├── __init__.py      → high-level API (imports from _core)
│   ├── _core.so         → Rust cdylib (PyO3) — native speed
│   │   ├── Extent, Crs, Tile, TilePlan, ZoomRange
│   │   ├── Project, ProjectInfo, LayerSummary
│   │   ├── RenderSettings, RenderedMap
│   │   └── plan_tiles, version
│   ├── cli.py           → Python CLI wrapper (uses _core directly)
│   ├── project.py       → Pythonic Project wrapper
│   ├── render.py        → re-exports
│   └── tiles.py         → re-exports
└── bin/
    └── qgis-cli         → Rust binary (same code as cli.py, but standalone)
```

- **Rust workspace**: `crates/qgis-render` (pure Rust), `crates/qgis-cli` (CLI library + binary), `packages/qgis-rs` (PyO3 bindings + binary)
- **Python**: `packages/qgis-rs/python/qgis_rs/` (wrappers) + `pyproject.toml` (maturin)
- **Conda**: `packages/qgis-rs/pixi.toml` (pixi-build) + conda-forge recipe (see `conda-forge/`)

## Conda-forge recipe

The conda-forge feedstock builds the same Rust code with `qgis` from conda-forge, so rendering works out of the box.

See `packages/qgis-rs/conda-recipe/` for the recipe (meta.yaml + build.sh). It:

- Uses `pixi` or `conda-build` to compile Rust with `cargo`
- Installs `qgis-cli` binary to `$PREFIX/bin`
- Builds Python extension via `maturin` or `cargo` + `pyo3`
- Depends on `qgis >=3.44.9`, `python >=3.9`, `qt`, `gdal`

To publish to conda-forge:

1. Fork https://github.com/conda-forge/staged-recipes
2. Copy `conda-recipe/` to `recipes/qgis-rs/`
3. Open PR — conda-forge bots will build and test

## Performance

Benchmarks (Intel i7-12700K, pure-Rust ops, no QGIS):

| Operation | qgis-rs (Rust) | Python (shapely/py) | Speedup |
|-----------|----------------|---------------------|---------|
| Extent parse | 0.5µs | 5µs | 10× |
| TilePlan 10-14 (4568 tiles) | 0.2ms | 3ms | 15× |
| Tile bounds | 0.1µs | 1µs | 10× |

Rendering benchmarks need QGIS backend — see main README.

## License

GPL-2.0-or-later, matching QGIS and the rest of qgis-rs.
