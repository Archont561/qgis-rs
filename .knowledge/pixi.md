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
| `taplo`        | —             | TOML format check (`lint-toml`)   |
| `actionlint`   | —             | GitHub Actions lint (`lint-actions`) |

### Feature Layers

Dependencies live in features (mirroring the pixi-sandbox reference project), so
each environment installs only what it needs; the root `[dependencies]` table is
deliberately empty. The feature set:

| Feature     | Contents                                        |
|-------------|-------------------------------------------------|
| `rust`      | `rust`                                          |
| `cxx`       | `cxx-compiler`, `clang-tools`                   |
| `qgis`      | `qgis`                                          |
| `utils`     | `lefthook`, `convco`, `taplo`, `actionlint`     |
| `docs`      | `bun`                                           |
| `sandbox`   | no deps; `sandbox-restore` task                |
| `sdk`       | `qgis-sdk` (source), `maturin`, `rust`, `pytest` + PyQGIS activation env |
| `py`        | `python`, `maturin`, `qgis-rs` (source), `pytest` |
| `node`      | `nodejs`, `rust`                                |

### Feature: `qgis`

```toml
[feature.qgis.dependencies]
qgis = ">=3.44.9,<4"
```

The QGIS dependency is in a feature so that lightweight tasks (formatting, linting Rust code) don't require downloading the entire QGIS stack.

There is no `default` environment. The `dev` environment activates the
`rust`, `cxx`, `qgis`, `utils`, and `sandbox` features; every user-facing task
sets `default-environment` so bare `pixi run <task>` works, and CI passes `-e`
explicitly.

### Feature: `docs`

`bun >=1.2,<2` plus the `docs-dev` / `docs-build` / `docs-preview` tasks. See
[documentation-site.md](/documentation-site.md). The `docs` env is also where
JS **testing** runs — the root `node-test` task and CI both invoke bun here,
because bun cannot share an environment with QGIS (icu, see below).

### Feature: `sdk`

The Python plugin SDK. It adds the `qgis-sdk` workspace package and `pytest`,
and exports the PyQGIS paths at activation:

```toml
[feature.sdk.dependencies]
qgis-sdk = { path = "./py-packages/qgis-sdk" }
pytest   = ">=8,<9"

[feature.sdk.activation.env]
PYTHONPATH       = "$CONDA_PREFIX/share/qgis/python/plugins:$CONDA_PREFIX/share/qgis/python:$PYTHONPATH"
QGIS_PREFIX_PATH = "$CONDA_PREFIX"
QT_QPA_PLATFORM  = "offscreen"
```

### Environments

| Environment | Features                                         | Solve group | Purpose |
|-------------|--------------------------------------------------|-------------|---------|
| `dev`       | `rust`, `cxx`, `qgis`, `py-runtime`, `utils`, `sandbox` | `dev` | Rust/C++/Python development and tests |
| `ci`        | `rust`, `cxx`, `qgis`, `sandbox`                 | `ci`        | What CI actually runs (parity) |
| `utils`     | `utils`                                          | `utils`     | Hook / lint tooling only |
| `docs`      | `docs`                                           | `docs`      | Astro docs site + bun JS tests |
| `sdk`       | `qgis`, `sdk`                              | `sdk`       | Python plugin SDK |
| `py`        | `py`                                       | `py`        | qgis-rs wheel, no QGIS |
| `py-qgis`   | `qgis`, `py`                               | `py-qgis`   | qgis-rs wheel with QGIS |
| `node`      | `node`                                     | `node`      | qgis-rs npm package |

`sdk` has its own solve group on purpose. Building `qgis-sdk` from source needs
the `pixi-build-python` backend from `prefix.dev`; keeping `sdk` out of the
other groups means `pixi install -e dev` and `-e ci` never need it.

The `docs` feature (bun, icu <76) is deliberately **not** in `dev`/`ci`:
conda-forge QGIS needs icu ≥78.3, so the two cannot share an environment — docs
tasks run against the separate `docs` environment.

> **Gotcha (pixi 0.81):** `default-environment` is only accepted on tasks that
> have a `cmd`, declared inline in the single `[tasks]` table. Pure aggregators
> (`gates`, `ci`, `ci-full`) omit it — pixi resolves their environment through
> the tasks they `depends-on`.

## Python and PyQGIS

**Python is never declared as a dependency.** The conda-forge `qgis` package
depends on the interpreter its bindings were built against, so it arrives as
part of the QGIS environment — for QGIS 3.44.9 that is CPython 3.14
(`python-3.14.6-…_cp314` in `pixi.lock`). Declaring `python` separately could
only drift away from the bindings.

**Import resolution.** The bindings are *not* in `site-packages`; they live at:

```
$CONDA_PREFIX/share/qgis/python           # qgis.core, qgis.gui, qgis.utils, …
$CONDA_PREFIX/share/qgis/python/plugins   # bundled plugin modules
```

The conda-forge package exports those through
`etc/conda/activate.d/qgis-activate.sh`, which also sets `QGIS_PREFIX_PATH` and
`QT_PLUGIN_PATH`. Pixi runs activation scripts provided by installed packages
for `pixi run` and `pixi shell`, so `import qgis.core` just works inside a pixi
task. The `sdk` feature repeats the same variables in `activation.env` so the
paths are explicit in the manifest rather than implicit in a package script.

`qgis_sdk.runtime.require_qgis()` prints those paths when an import fails,
which is the fastest way to diagnose a broken environment.

## Workspace Packages

The manifest is a **pixi workspace**: `[workspace]` carries `preview =
["pixi-build"]`, and a sub-directory manifest can then declare a `[package]`
section that pixi builds into a conda package.

```
py-packages/qgis-sdk/
├── pixi.toml      # [package] only — no [workspace], it is inherited
├── pyproject.toml # PEP 517 metadata; [tool.maturin].manifest-path = ../../crates/qgis-sdk
├── src/qgis_sdk/  # pure-Python layer
└── tests/

crates/qgis-sdk/   # the Rust core: PyO3 _core + the qgis-plugin / qgis-sdk CLIs
```

The Rust half deliberately lives in the Cargo workspace rather than inside the
Python directory, so `cargo check --workspace` covers it without a `[package]`
in `py-packages/`. maturin reaches it through
`[tool.maturin] manifest-path = "../../crates/qgis-sdk/Cargo.toml"`, and every
path in `[tool.maturin]` stays relative to this directory — which is what keeps
`python-source = "src"` pointing at the Python sources. A PEP 517 build that
copies the project out of the checkout (an sdist) would not see the crate, so
wheels are built from a clone: `pip install ./py-packages/qgis-sdk`, pixi
(`pixi run -e sdk sdk-build`) and the conda recipe all build in place. Note that
maturin's own `-m` flag accepts only a `Cargo.toml` — the pyproject -> crate hop
is driven by the *working directory*, so the CLI form is
`cd py-packages/qgis-sdk && maturin build`.

```toml
# py-packages/qgis-sdk/pixi.toml
[package]
name    = "qgis-sdk"
version = "0.1.0"

[package.build.backend]
name     = "pixi-build-python"
version  = "*"
channels = ["https://prefix.dev/pixi-build-backends", "https://prefix.dev/conda-forge"]

[package.host-dependencies]
hatchling = "*"        # PEP 517 backend; pixi-build-python adds python + uv itself

[package.run-dependencies]
qgis = ">=3.44.9,<4"   # brings PyQGIS *and* its Python interpreter
```

Consumers add it as a source dependency (`qgis-sdk = { path = "..." }`);
`pixi install` / `pixi run` build it automatically, and `pixi publish` builds a
`.conda` for packages that opt in with `publish = true`.

`pixi-build` is still a preview feature upstream, so the flag has to stay in
`[workspace].preview` until it stabilises.

> **Gotcha:** `_*` in `.gitignore` used to swallow every `__init__.py`, and
> hatchling honours VCS ignore files — the built wheel silently became an empty
> namespace package. `.gitignore` now negates `__init__.py` and `__main__.py`.

> **Task fields:** `cmd`, `args`, `depends-on`, `cwd`, `env`, `input`, `output`,
> `description` and `default-environment` (the environment to run in when the task
> is invoked without `-e`, e.g. `docs-build`) — copied from the reference project,
> and anything else is rejected.

> **Gotcha:** a task table written as `[tasks.<name>]` swallows every `key = value`
> line that follows it, so an umbrella task appended at the end of the file is
> parsed as a *field of* that task and pixi rejects the whole manifest
> ("Unexpected keys, expected only 'cmd', 'inputs', …"). Plain verbs belong in the
> single `[tasks]` table; only tasks that need `args`/multi-line `cmd` get a
> `[tasks.<name>]` table, and they go last.

## Tasks

Task verbs follow the pixi-sandbox convention — one action per verb, and the
umbrella task is what CI is expected to reproduce locally.

### Formatting
- `fmt-rs` — `cargo fmt --all`
- `fmt-cpp` — `clang-format -i` on all `.cpp` and `.h` files
- `fmt` — runs both
- `fmt-check` — `cargo fmt --all --check`, the gate the formatters exist to satisfy

### Linting
- `clippy` — `cargo clippy --workspace --all-targets -- -D warnings`
- `check-cpp` — `clang-format --dry-run --Werror` over the shims (staged files via `--` args, whole tree otherwise)
- `lint-cpp` — `clang-tidy` with sysroot, Qt, and QGIS includes (depends on `_build-for-lint`)
- `lint` — `clippy` + `lint-cpp`
- `lint-commit` — `convco check --from-stdin` (commit-msg hook)
- `lint-toml` — `taplo fmt --check` (staged files via `--` args; bare form checks `pixi.toml` + `.pixi-sandbox.toml`)
- `lint-actions` — `actionlint` on `.github/workflows`

### Build & gates
- `build` — `cargo build --release`
- `gates` — `fmt-check` + `clippy` + `lint-toml` + `lint-actions` + `test`; the "CI will be green" check
- `ci` — `gates` + `check-cpp`
- `ci-full` — `ci` + `lint-cpp` + `test-full` (needs the `dev` env installed)
- `sandbox-restore` — `scripts/restore.sh`: fetch the published sandbox branch
  (`sandbox/developer-linux-64`) and restore `dev`/`docs` offline

### Testing
- `test` — basic tests (`application_info`), with optional `--clean` flag
- `test-full` — full tests including `application_lifecycle` and `vector_layer`
- `node-test` — `bun test tests/contract.test.js` for `ts-packages/qgis-node`,
  run in the `docs` env (bun); depends on `node-build` in the `node` env, so a
  bare `pixi run node-test` builds the addon and then tests it on bun

Both set:
- `QT_QPA_PLATFORM=offscreen` — prevents Qt display requirement
- `PROJ_DATA=$CONDA_PREFIX/share/proj` — PROJ data location
- `QGIS_PLUGINPATH=$CONDA_PREFIX/lib/qgis/plugins` — provider plugins

### Internal
- `setup` — creates a symlink: `libqca-qt5.so.2` → `libqca-qt6.so.2`
- `_build-for-lint` — builds qgis-sys so clang-tidy can find generated headers

### Scaffolding
- `scaffold <layer> <concept> <qgis_class> <short_name>` — generates new FFI boilerplate


## Common Commands

```bash
pixi shell                  # enter the `dev` environment
pixi run fmt                # format everything
pixi run lint               # lint everything
pixi run test               # run basic tests
pixi run test-full          # run all tests
pixi run scaffold core raster QgsRasterLayer raster

pixi install -e sdk         # build + install the qgis-sdk workspace package
pixi run -e sdk sdk-test    # pytest for py-packages/qgis-sdk
pixi run -e sdk sdk-doctor  # print interpreter, PYTHONPATH, and prove the imports
```

## Offline / Sandbox Bootstrapping

When pixi is not available (e.g., sandboxed CI, restricted network environments),
the qgis-rs environment can be restored from the published **pixi-sandbox branch**:

```bash
bash scripts/restore.sh
# fetches sandbox/developer-linux-64, doctor-verifies, restores dev/docs,
# sources .pixi/sandbox-env.sh (cargo, rustc, clang-tools, QGIS, bundled pixi)
```

This provides cargo, rustc, clang-tools, QGIS headers/libraries, and pixi itself
without needing conda-forge or prefix.dev. See [env-provisioning.md](/env-provisioning.md)
for the full design.

The `.github/workflows/publish_sandbox.yml` workflow calls the pixi-sandbox
*reusable* publisher after every successful `CI` run on `main` (or on manual
dispatch), validates `.pixi-sandbox.toml`, and republishes the bundle whenever
`pixi.toml` / `pixi.lock` change. The branch is `sandbox/developer-linux-64`.
