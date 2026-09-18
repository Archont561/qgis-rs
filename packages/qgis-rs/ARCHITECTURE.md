# qgis-rs Python package — Architecture

## Goal

Expose the QGIS SDK CLI tool (`qgis-cli`) as a Rust-based binary inside a Python package, installable from pip and conda-forge, with both API and CLI at native speed.

## Design

### Two artifacts, one Rust codebase

1. **Rust binary `qgis-cli`** — standalone executable, built with `cargo build --release --bin qgis-cli`. Does argument parsing with `clap` and dispatches to `qgis-render` / `qgis-server`. When installed via `pip install qgis-rs`, maturin places this binary on PATH (`$VENV/bin/qgis-cli` or `$CONDA_PREFIX/bin/qgis-cli`).

2. **Rust cdylib `_core`** — PyO3 extension module `qgis_rs._core` (`_core.so` / `.pyd`). Exposes pure-Rust types (`Extent`, `Crs`, `Tile`, `TilePlan`, `ZoomRange`, `Project`, etc.) at native speed. Python wrappers in `python/qgis_rs/` import from `_core` and provide high-level API.

Both artifacts share the same Rust code: `crates/qgis-render` (pure Rust, no QGIS) and `crates/qgis-cli` (now a lib + bin, so `qgis-rs` package can reuse its `cli` and `commands` modules).

### Python package layout

```
packages/qgis-rs/
├── Cargo.toml              # Rust crate: cdylib _core + bin qgis-cli
├── pyproject.toml          # maturin build, console scripts qgis-cli / qgis-rs
├── src/
│   ├── lib.rs              # PyO3 bindings for qgis-render
│   └── bin/qgis-cli.rs     # Binary entry point (calls qgis_cli::main_entry)
├── python/qgis_rs/
│   ├── __init__.py         # Tries _core, falls back to _fallback.py
│   ├── _fallback.py        # Pure-Python implementation (dev without cargo)
│   ├── _core.pyi           # Type stubs
│   ├── cli.py              # Python CLI wrapper (uses _core directly, no subprocess)
│   ├── project.py          # High-level Project wrapper
│   ├── render.py           # re-exports
│   └── tiles.py            # re-exports
├── tests/
│   ├── test_api.py         # API tests (pure Rust, no QGIS)
│   └── test_cli.py         # CLI tests
├── pixi.toml               # pixi-build-python package manifest
├── conda-recipe/
│   ├── meta.yaml           # conda-forge recipe (binary + Python extension)
│   └── README.md
└── README.md               # User-facing docs
```

### Build systems

- **pip (PyPI)**: `maturin` builds wheel with both `_core` extension and `qgis-cli` binary. `pyproject.toml` declares `[project.scripts] qgis-cli = "qgis_rs.cli:main"` for Python wrapper, plus maturin installs Rust binary as `qgis-cli` executable. Pre-built wheels for Linux, macOS, Windows — no cargo needed for end users.

- **conda-forge**: `conda-recipe/meta.yaml` builds Rust binary with `cargo build --release`, copies to `$PREFIX/bin`, then builds Python wheel with `maturin` and `pip install`. Depends on `qgis >=3.44.9` optionally — lightweight variant (no QGIS) supports `info`, `tiles --dry-run`, `version`; full variant (with QGIS) supports `render`, `tiles`, `export`, `serve`.

- **pixi**: `pixi.toml` defines `qgis-rs` as source dependency built with `pixi-build-python` (maturin backend). Environments `py` (pure) and `py-qgis` (with QGIS) for testing.

### Fallback for development without cargo

When `_core` extension is not built (e.g., in sandbox without cargo), `__init__.py` falls back to `_fallback.py` — pure-Python implementation of same API, slower but functional. This allows `pytest` to pass without Rust toolchain, and `python -m qgis_rs.cli` to work.

In production wheels, `_core` is always present, so fallback is never used — users get native speed.

### Native speed guarantees

- **API**: `Extent.parse`, `TilePlan`, `ZoomRange`, `Crs`, `plan_tiles`, `Project.open`, etc. are Rust structs exposed via PyO3 `#[pyclass]` — no Python overhead for geometry math.
- **CLI**: `qgis-cli` binary is Rust executable (no Python interpreter). `qgis_rs.cli:main` Python wrapper calls Rust extension directly (no subprocess), so `python -m qgis_rs.cli` is also native speed.

### Future: QGIS backend

Currently `qgis-render` is pure Rust (no `libqgis_core`). Rendering methods return `Error::Unimplemented` until QGIS backend is wired. When `qgis-sys` backend lands:

- `Project::render` will use `libqgis_core` via CXX bindings (still Rust, still native speed, but requires QGIS libs).
- Conda-forge package will depend on `qgis` to provide `libqgis_core.so`.
- pip wheels will remain lightweight (no QGIS) unless we bundle QGIS — for full rendering, users should use conda-forge.

### Testing

- `cargo test -p qgis-render -p qgis-cli` — Rust unit tests (no QGIS needed for pure ops)
- `python -m pytest packages/qgis-rs/tests -v` — Python API + CLI tests (uses fallback if _core missing, _core if built)
- `maturin develop && pytest` — full test with Rust extension
- `pixi run -e py py-test` — via pixi environment
- `qgis-cli --help`, `qgis-cli tiles ... --dry-run` — CLI smoke tests

### Publishing

- **PyPI**: GitHub workflow `.github/workflows/python.yml` builds wheels via `PyO3/maturin-action` on Linux, macOS, Windows and publishes on tag.
- **conda-forge**: Copy `conda-recipe/` to `conda-forge/staged-recipes/recipes/qgis-rs/` and open PR.
