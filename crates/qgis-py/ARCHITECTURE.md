# qgis-rs Python package — Architecture

Crate: `crates/qgis-py` · Distribution: `py-packages/qgis-py`

## Goal

Expose the QGIS SDK CLI tool (`qgis-cli`) as a Rust-based binary inside a Python package, installable from pip and conda-forge, with both API and CLI at native speed.

## Design

### Two artifacts, one Rust codebase

1. **Rust binary `qgis-cli`** — standalone executable, built with `cargo build --release -p qgis-cli`. Does argument parsing with `clap` and dispatches to `qgis-render` / `qgis-server`. It lives in `crates/qgis-cli`, not here: bin names must be unique across the workspace (every bin resolves to the same `target/<profile>/<name>`), and maturin's `pyo3` bindings never ship bin targets in the wheel anyway. On PATH, pip installs provide `qgis-cli` as the `[project.scripts]` console script (`qgis_py.cli:main`); the conda recipe additionally installs the real Rust binary into `$PREFIX/bin`.

2. **Rust cdylib `_core`** — PyO3 extension module `qgis_py._core` (`_core.so` / `.pyd`). It exposes **one function**, `invoke(request_json) -> response_json`, which is `qgis_engine::invoke` and nothing else. No `#[pyclass]` per domain type: the FFI surface is the wire protocol of `crates/qgis-protocol` (see `.knowledge/decisions/D09-wire-protocol-over-ffi.md`), and the ergonomic `Extent`/`Crs`/`TilePlan`/`Project` classes are plain Python in `python/qgis_py/_api.py` over that one call.

Both artifacts share the same Rust code: `crates/qgis-engine` (the dispatcher), `crates/qgis-render` (pure Rust, no QGIS) and `crates/qgis-cli` (a lib + bin, so the `qgis-rs` package can reuse its `cli` and `commands` modules).

### Python package layout

The crate and the distribution live in separate trees: this directory is Rust,
the Python-facing half sits in `py-packages/qgis-py/`.

```
crates/qgis-py/               # this crate — pure Rust, no Python files
├── Cargo.toml                # cdylib _core only (no bin targets)
├── src/
│   └── lib.rs                # the one #[pyfunction]: invoke(request_json)
└── tests/
    └── adapter.rs            # the adapter adds nothing to the request (D11)

py-packages/qgis-py/          # the Python distribution
├── pyproject.toml            # maturin build, console scripts qgis-cli / qgis-rs
│                             # [tool.maturin].manifest-path = ../../crates/qgis-py/Cargo.toml
├── python/qgis_py/
│   ├── __init__.py         # Public API surface (re-exports from _api)
│   ├── _transport.py       # invoke(): JSON in, JSON out, errors -> exceptions
│   ├── _api.py             # Extent, Crs, Tile, TilePlan, ZoomRange, Project
│   ├── _core.pyi           # Type stubs for the one native function
│   ├── cli.py              # Python CLI wrapper (uses _api directly, no subprocess)
│   ├── project.py          # re-exports
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

- **pip (PyPI)**: `maturin` builds the wheel with the `_core` extension module. `pyproject.toml` declares `[project.scripts] qgis-cli = "qgis_py.cli:main"` for the Python wrapper; the Rust binary itself is installed by the conda recipe, since maturin ships only the extension module. Pre-built wheels for Linux x86_64 and arm64 — no cargo needed for end users.

- **conda-forge**: `conda-recipe/meta.yaml` builds the Rust binary with `cargo build --release -p qgis-cli`, copies to `$PREFIX/bin`, then builds the Python wheel with `cd py-packages/qgis-py && maturin build` and `pip install`. Depends on `qgis >=3.44.9` optionally — lightweight variant (no QGIS) supports `info`, `tiles --dry-run`, `version`; full variant (with QGIS) supports `render`, `tiles`, `export`, `serve`.

- **pixi**: `pixi.toml` defines `qgis-rs` as source dependency built with `pixi-build-python` (maturin backend). Environments `py` (pure) and `py-qgis` (with QGIS) for testing.

### No fallback

There used to be a `_fallback.py` re-implementing the API in Python for
environments without cargo. It is gone: a second implementation of tiling maths
is a second set of answers, and the whole point of this package is that the
answers come from Rust. Importing `qgis_py` without a built `_core` now raises
immediately, with the ImportError that caused it, instead of quietly serving
numbers from a different codebase.

### Native speed guarantees

- **API**: every value — `Extent.parse`, `TilePlan`, `ZoomRange`, `Crs`, `plan_tiles`, `Project.open` — is computed by Rust and crosses the boundary once, as JSON. The Python classes hold the decoded result; they never recompute it.
- **CLI**: `qgis-cli` binary is Rust executable (no Python interpreter). `qgis_py.cli:main` Python wrapper calls Rust extension directly (no subprocess), so `python -m qgis_py.cli` is also native speed.

### Native QGIS backend

`qgis-render` remains the backend-agnostic Rust domain layer; its pure
`Project::render` method is intentionally separate from the native manager.
The transport-level `render_map` and `export_features` operations route through
`qgis-engine` to `qgis-sys` when the `qgis` feature is enabled. That manager is
the sole owner of `libqgis_core`, Qt objects, project state, and path-based
artifact creation.

- The QGIS-enabled Pixi/conda environment provides `libqgis_core.so` and runs
  the native-manager integration tests.
- QGIS-free builds retain validation and pure Rust operations, but report native
  render/export tools as unavailable instead of silently substituting another
  implementation.
- pip wheels remain lightweight unless a distribution explicitly supplies the
  native QGIS runtime; users needing native rendering should use the QGIS-backed
  package/environment.

### Testing

- `cargo test -p qgis-render -p qgis-cli -p qgis-py -p qgis-sdk -p qgis-node` — Rust logic, CLI, and binding-adapter tests (QGIS is only needed for `qgis-sys` integration tests)
- `cargo test -p qgis-protocol -p qgis-engine` — the wire protocol and one test per operation, at the JSON level the bindings see
- `maturin develop && python -m pytest py-packages/qgis-py/tests -v` — the Python client against the real `_core`
- `bun x turbo run test --filter=qgis-py-dist` — builds the extension, then runs the native Python tests
- `qgis-cli` behavior is covered by Rust integration tests in `crates/qgis-cli/tests/cli.rs`; plugin CLI behavior is covered in `crates/qgis-sdk/tests/plugin_cli.rs`

### Publishing

- **CI**: `.github/workflows/ci.yml` builds the Python extensions with maturin, runs API/CLI smoke tests, and records Python coverage. Wheel publishing is not part of the current workflow set.
- **conda-forge**: Copy `conda-recipe/` to `conda-forge/staged-recipes/recipes/qgis-rs/` and open PR.
