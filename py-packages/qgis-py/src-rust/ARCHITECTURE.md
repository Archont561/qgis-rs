# qgis-py — Architecture

Crate: `py-packages/qgis-py/src-rust` · Distribution: `py-packages/qgis-py`

## Goal

Expose the QGIS engine to Python as a thin FFI API. Python holds no answers of its own: every question is asked of the Rust engine, and the engine starts or attaches to QGIS programmatically when a call needs it. The package ships **no command-line interface**. The standalone CLI is `crates/qgis-cli`, a separate product that depends on the Rust crates, not on any binding.

## Design

### One artifact: the `_core` extension

Rust cdylib `_core`, the PyO3 extension module `qgis_py._core` (`_core.so` / `.pyd`). It exposes **one function**, `invoke(request_json) -> response_json`, which is `qgis_engine::invoke` and nothing else. There is no `#[pyclass]` per domain type. The FFI surface is the wire protocol of `crates/qgis-protocol` (see `.knowledge/decisions/D09-wire-protocol-over-ffi.md`), and the ergonomic `Extent`, `Crs`, `TilePlan`, and `Project` classes are plain Python in `python/qgis_py/_api.py` over that one call.

QGIS runs inside the engine. The native manager (`crates/qgis-sys`) owns `libqgis_core`, the Qt objects, and project state. Its `app_init` operation calls `QgsApplication::initQgis()` in-process, so a Python caller never starts QGIS itself. The engine shares this path with the Node binding.

### Python package layout

The crate and the distribution live in separate trees: this directory is Rust, and the Python-facing half sits in `py-packages/qgis-py/`.

```
py-packages/qgis-py/src-rust/               # this crate — pure Rust, no Python files
├── Cargo.toml                # cdylib _core only (no bin targets)
├── src/
│   └── lib.rs                # the one #[pyfunction]: invoke(request_json)
└── tests/
    └── adapter.rs            # the adapter adds nothing to the request (D11)

py-packages/qgis-py/          # the Python distribution
├── pyproject.toml            # maturin build; no [project.scripts]
│                             # [tool.maturin].manifest-path = src-rust/Cargo.toml
├── python/qgis_py/
│   ├── __init__.py         # Public API surface (re-exports from _api)
│   ├── _transport.py       # invoke(): JSON in, JSON out, errors -> exceptions
│   ├── _api.py             # Extent, Crs, Tile, TilePlan, ZoomRange, Project
│   ├── _core.pyi           # Type stubs for the one native function
│   ├── project.py          # re-exports
│   ├── render.py           # re-exports
│   └── tiles.py            # re-exports
├── tests/
│   └── test_api.py         # API tests (pure Rust, no QGIS)
├── pixi.toml               # pixi-build-python package manifest
├── recipes/qgis-py/
│   ├── meta.yaml           # conda-forge recipe (Python extension only)
│   └── README.md
└── README.md               # User-facing docs
```

### Build systems

- **pip (PyPI)**: `maturin` builds the wheel with the `_core` extension module. The wheel has no console scripts and no bundled binary. Pre-built wheels are published for Linux x86_64 and arm64, so end users need no cargo.
- **conda-forge**: `recipes/qgis-py/meta.yaml` builds the Python wheel with `maturin build` and installs it with `pip`. It declares no entry points and installs no binary.
- **pixi**: `pixi.toml` defines `qgis-py` as a source dependency built with `pixi-build-python` (maturin backend).

### No fallback

There used to be a `_fallback.py` re-implementing the API in Python for environments without cargo. It is gone: a second implementation of tiling maths is a second set of answers, and the whole point of this package is that the answers come from Rust. Importing `qgis_py` without a built `_core` raises immediately, with the ImportError that caused it, instead of quietly serving numbers from a different codebase.

### Native speed guarantees

Every value (`Extent.parse`, `TilePlan`, `ZoomRange`, `Crs`, `plan_tiles`, `Project.open`) is computed by Rust and crosses the boundary once, as JSON. The Python classes hold the decoded result and never recompute it.

### Native QGIS backend

`qgis-render` remains the backend-agnostic Rust domain layer, and its pure `Project::render` method is intentionally separate from the native manager. The transport-level `render_map` and `export_features` operations route through `qgis-engine` to `qgis-sys` when the `qgis` feature is enabled. That manager is the sole owner of `libqgis_core`, Qt objects, project state, and path-based artifact creation.

- The QGIS-enabled Pixi/conda environment provides `libqgis_core.so` and runs the native-manager integration tests.
- QGIS-free builds keep validation and pure Rust operations, but report native render and export as unavailable instead of silently substituting another implementation.
- pip wheels remain lightweight unless a distribution explicitly supplies the native QGIS runtime. Users who need native rendering should use the QGIS-backed package or environment.

### Testing

- `cargo test -p qgis-render -p qgis-py -p qgis-sdk -p qgis-node` — Rust logic and binding-adapter tests (QGIS is only needed for `qgis-sys` integration tests)
- `cargo test -p qgis-protocol -p qgis-engine` — the wire protocol and one test per operation, at the JSON level the bindings see
- `maturin develop && python -m pytest py-packages/qgis-py/tests -v` — the Python client against the real `_core`
- `bun x turbo run test --filter=qgis-py-dist` — builds the extension, then runs the native Python tests
- `tests/test_no_cli.py` — guards that the package declares no console scripts and carries no CLI module or bundled binary

### Publishing

- **CI**: `.github/workflows/ci.yml` builds the Python extensions with maturin and records Python coverage.
- **Release**: `xtask release build-artifacts` builds the wheels (see `.knowledge/release.md`).
- **conda-forge**: copy `recipes/qgis-py/` to `staged-recipes/recipes/qgis-py/` and open a PR.
