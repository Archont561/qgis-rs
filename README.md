# qgis-rs

<p align="center">
  <strong>Safe, idiomatic Rust bindings for <a href="https://qgis.org/">QGIS</a> — the world's most popular open-source GIS platform.</strong><br>
  Render publication-quality maps, process geospatial data at native speed, and build high-performance GIS servers.
</p>

<p align="center">
  <!-- pipeline -->
  <a href="https://github.com/Archont561/qgis-rust/actions/workflows/ci.yml"><img src="https://github.com/Archont561/qgis-rust/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/gh/Archont561/qgis-rust"><img src="https://codecov.io/gh/Archont561/qgis-rust/branch/main/graph/badge.svg" alt="Coverage"></a>
  <a href="https://codecov.io/gh/Archont561/qgis-rust"><img src="https://img.shields.io/codecov/c/github/Archont561/qgis-rust/main?token=&label=rust%20%2B%20python%20coverage&logo=codecov" alt="Combined coverage"></a>
  <a href="https://github.com/Archont561/qgis-rust/actions/workflows/docs.yml"><img src="https://github.com/Archont561/qgis-rust/actions/workflows/docs.yml/badge.svg" alt="Docs"></a>
  <a href="https://github.com/Archont561/qgis-rust/actions/workflows/release.yml"><img src="https://github.com/Archont561/qgis-rust/actions/workflows/release.yml/badge.svg" alt="Release"></a>
</p>

<p align="center">
  <!-- distribution -->
  <a href="https://github.com/Archont561/qgis-rust/releases"><img src="https://img.shields.io/github/v/release/Archont561/qgis-rust?label=release&logo=github" alt="Latest release"></a>
  <a href="https://crates.io/crates/qgis-render"><img src="https://img.shields.io/crates/v/qgis-render?logo=rust&label=crates.io" alt="crates.io"></a>
  <a href="https://docs.rs/qgis-render"><img src="https://img.shields.io/docsrs/qgis-render?logo=docsdotrs&label=docs.rs" alt="docs.rs"></a>
  <a href="https://pypi.org/project/qgis-py/"><img src="https://img.shields.io/pypi/v/qgis-py?logo=pypi&logoColor=white&label=PyPI" alt="PyPI"></a>
  <a href="https://www.npmjs.com/package/@archont561/qgis-node"><img src="https://img.shields.io/npm/v/qgis-rs?logo=npm&label=npm" alt="npm"></a>
  <a href="https://prefix.dev/channels/@archont561/qgis-rs"><img src="https://img.shields.io/badge/prefix.dev-%40archont561%2Fqgis--rs-5c4ee5?logo=condaforge" alt="prefix.dev channel"></a>
</p>

<p align="center">
  <!-- platform and process -->
  <a href="https://spdx.org/licenses/GPL-2.0-or-later.html"><img src="https://img.shields.io/badge/license-GPL--2.0--or--later-blue" alt="License: GPL-2.0-or-later"></a>
  <a href="https://qgis.org/"><img src="https://img.shields.io/badge/QGIS-3.44.9%2B-589632?logo=qgis&logoColor=white" alt="QGIS 3.44.9+"></a>
  <a href="https://www.rust-lang.org/"><img src="https://img.shields.io/badge/Rust-1.96-orange?logo=rust" alt="Rust 1.96"></a>
  <a href="https://pixi.sh/"><img src="https://img.shields.io/badge/Pixi-0.81%2B-yellow?logo=condaforge" alt="Pixi 0.81+"></a>
  <a href="https://bun.sh/"><img src="https://img.shields.io/badge/Bun-1.3%2B-fbf0df?logo=bun&logoColor=black" alt="Bun 1.3+"></a>
  <img src="https://img.shields.io/badge/platform-linux--64-brightgreen?logo=linux&logoColor=white" alt="linux-64">
  <a href="https://www.conventionalcommits.org/"><img src="https://img.shields.io/badge/commits-conventional-fe5196?logo=conventionalcommits&logoColor=white" alt="Conventional Commits"></a>
  <a href="https://github.com/Archont561/qgis-rust/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs welcome"></a>
</p>

<p align="center">
  <a href="https://archont561.github.io/qgis-rust/">Documentation</a> ·
  <a href="https://docs.rs/qgis-render">API Reference</a> ·
  <a href="#-release-model">Release model</a> ·
  <a href="#-contributing">Contributing</a>
</p>

---

## Overview

**qgis-rs** brings the full power of QGIS to Rust through safe, zero-cost CXX bindings — and ships that
engine to Python, TypeScript and the command line from a single workspace.

```rust
use qgis_render::{Project, RenderSettings};

let project = Project::open("map.qgs")?;
project.render_to_file(
    &RenderSettings::new(1920, 1080),
    "output.png"
)?;
```

> [!NOTE]
> This project is in active development. The API is stabilizing — expect minor breaking changes before v1.0.

## Why qgis-rs?

| Benefit | What it means |
| --- | --- |
| 🚀 **Native performance** | Render QGIS projects at C++ speed with zero Python overhead. Batch-process thousands of maps in minutes. |
| 🛡️ **Type safety** | Catch errors at compile time, without runtime crashes from mismatched types or null pointers. |
| 🎨 **Full QGIS styling** | Use existing `.qgs` projects with symbology, labels, and print layouts — no SLD conversion needed. |
| 📦 **Single binary** | Deploy as a standalone executable without a JVM or Python runtime. |
| 🔁 **One version everywhere** | Rust crates, wheels, npm tarballs and conda packages are cut from one tag, with one checksum file. |

## Features

- **Project Rendering** — Load `.qgs`/`.qgz` files and render to PNG/JPEG/SVG/PDF
- **Tile Generation** — Create XYZ/MBTiles/PMTiles pyramids with parallel workers
- **Data Access** — Iterate features, query attributes, perform spatial operations
- **Expression Engine** — Evaluate QGIS expressions with full function support
- **Print Layouts** — Render composer layouts with maps, legends, scale bars
- **HTTP Server** — Serve WMS/WFS/OGC APIs with built-in caching
- **CLI Tool** — Command-line interface for all operations
- **Plugin SDK** — Build QGIS plugins in Python with optional Rust acceleration

## Installation

### Python (pip / conda-forge) + TypeScript (npm)

The easiest way — no Rust or QGIS needed for many operations. Three packages:

- **`qgis-py`** (Python) — a curated Python API for QGIS, a PyQGIS replacement; rendering, tiling, project inspection (native Rust)
- **`qgis-sdk`** (Python) — plugin development SDK (Python + Rust-native CLI)
- **`qgis-rs`** (npm) — same rendering/tiling + plugin tools for Node.js/TypeScript

```bash
# Python — from PyPI (wheels carry the Rust binaries)
pip install qgis-py qgis-sdk

# Python — from conda-forge, with the QGIS backend for full rendering
conda install -c conda-forge qgis-py qgis-sdk
# or
pixi add qgis-py qgis-sdk

# TypeScript — from npm (NAPI addon + Rust binaries)
npm install @archont561/qgis-node
```

```bash
# Rendering tools (Python)
python -c "import qgis_py; print(qgis_py.__version__)"
qgis-cli info map.qgs --json
qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 --dry-run

# Plugin SDK (Python)
python -c "import qgis_sdk; print(qgis_sdk.__version__, qgis_sdk.HAS_RUST)"
qgis-sdk new my_plugin --type processing --rust

# TypeScript
node -e "const { TilePlan, Extent, ZoomRange } = require('@archont561/qgis-node'); console.log(new TilePlan(Extent.parse('14,50,15,51'), ZoomRange.parse('10-14')).tileCount())"
npx qgis-cli --help
```

Python API — rendering:

```python
from qgis_py import Project, Extent, TilePlan, ZoomRange

project = Project.open("map.qgs")
extent = Extent.parse("14,50,15,51")
plan = TilePlan(extent, ZoomRange.parse("10-14"))
print(f"Would render {plan.tile_count()} tiles")  # 4568, pure Rust, no QGIS
```

TypeScript API — same, native speed via NAPI:

```typescript
import { Project, Extent, TilePlan, ZoomRange } from '@archont561/qgis-node';

const plan = new TilePlan(Extent.parse('14,50,15,51'), ZoomRange.parse('10-14'));
console.log(plan.tileCount()); // 4568
```

Python API — plugin SDK:

```python
from qgis_sdk import Plugin, action, toolbar

class MyPlugin(Plugin):
    name = "My Plugin"
    version = "0.1.0"

    @toolbar("My Toolbar")
    @action(tooltip="Run my tool")
    def run_tool(self, iface):
        print("Hello from plugin!")
```

See the [Python docs](https://archont561.github.io/qgis-rust/getting-started/python/) and
[TypeScript docs](https://archont561.github.io/qgis-rust/getting-started/typescript/) for the full API.

### Rust (Cargo)

```toml
[dependencies]
qgis-render = "0.2"
```

Prerequisites: **Rust** ≥ 1.96.0, **QGIS** ≥ 3.44.9 (`libqgis_core`) for full rendering, and
**Pixi** (recommended) for a reproducible toolchain.

> [!IMPORTANT]
> You need QGIS development libraries for full rendering. Pure-Rust ops (tile planning, extent
> parsing) work without QGIS. See the [Installation Guide](https://archont561.github.io/qgis-rust/getting-started/installation/).

## Quick Start

### Render a QGIS project

```rust
use qgis_render::{Project, RenderSettings, Crs};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    qgis_render::init()?;

    let project = Project::open("my-map.qgs")?;
    let settings = RenderSettings::new(1920, 1080)
        .extent(project.extent())
        .crs(Crs::from_epsg(3857)?)
        .dpi(96);

    project.render_to_file(&settings, "output.png")?;
    Ok(())
}
```

### Generate tiles

```rust
use qgis_render::tiles::{TilePlan, TileFormat};

let plan = TilePlan::new()
    .zoom_range(10..=14)
    .bounds(project.extent())
    .tile_size(256)
    .format(TileFormat::Png);

plan.render_to_dir(&project, "./tiles/", 8)?;  // 8 parallel workers
```

### Access features

```rust
let layer = project.layer("buildings")?;
let vector = layer.as_vector()?;

for feature in vector.features().take(10) {
    println!("{}: height={}m", feature.get("name")?, feature.get("height")?);
}
```

## CLI Usage

```bash
qgis-cli render map.qgs -o output.png                  # render a project
qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 -o ./tiles/
qgis-cli serve map.qgs --port 8080                     # WMS/WFS server
qgis-cli info map.qgs                                  # inspect a project
qgis-cli mcp                                           # serve to an AI assistant over MCP
```

See the [CLI documentation](https://archont561.github.io/qgis-rust/cli/) for all commands.

## Architecture

```mermaid
graph TB
    subgraph "Your Application"
        A[qgis-render API]
    end

    subgraph "qgis-rs"
        B[qgis-sys CXX bindings]
    end

    subgraph "System"
        C[libqgis_core.so]
        D[Qt 6.x]
        E[GDAL/PROJ]
    end

    A -->|safe wrappers| B
    B -->|FFI| C
    C --> D
    C --> E
```

### Repository layout

```text
crates/        every Rust crate — protocol + engine, the QGIS stack, the PyO3 / NAPI cores, xtask
py-packages/   maturin projects: pyproject.toml + Python sources + tests
ts-packages/   Bun/npm projects: package.json + TS sources + tests
test-fixtures/ language-neutral test vectors every language reads (the bridge contract, layer goldens)
docs/          the Astro Starlight documentation site
backlog/       the Markdown task board (pixi run backlog) and its specification documents
scripts/       the few shell entry points that are still shell (see scripts/README.md)
.agents/       versioned agent skills, pinned by skills-lock.json
.knowledge/    design documents and decision records
```

Inside each of them the same split holds: **`src/` is code, `tests/` is tests** —
no `#[cfg(test)]` modules in Rust sources, no test files beside the module they
exercise ([D11](.knowledge/decisions/D11-tests-outside-src.md)).

### Crate / package structure

| Crate / Package | Purpose | Status |
|-----------------|---------|--------|
| `qgis-protocol` | The wire format spoken across every FFI boundary: `EngineRequest`/`EngineResponse`, the closed `Operation` enum, `TRANSPORT_VERSION` — plus `bridge`, the plugin-bridge envelopes and their validator | ✅ Active |
| `qgis-engine` | `invoke(request_json) -> response_json` — one dispatch arm per operation, and the only thing the bindings call | ✅ Active |
| `qgis-sys` | The native QGIS manager behind one C ABI `qgis_invoke`, and its C++ shim ([D12](.knowledge/decisions/D12-qgis-native-manager-over-c-abi.md)) | ✅ Active |
| `qgis-render` | High-level rendering API — extents, CRS, XYZ pyramids in pure Rust; QGIS-backed `render_map`/`export_features` through the native manager | ✅ Active |
| `qgis-server` | HTTP server (WMS/WFS/OGC) | 🔨 Scaffolded (routing works; listener pending) |
| `qgis-mcp` | Model Context Protocol server | ✅ Active (bundled into `qgis-cli mcp`) |
| `qgis-cli` | Command-line tool (Rust binary + lib) | 🔨 Scaffolded (`mcp`, `info`, `tiles --dry-run` work) |
| `qgis-styles` | Symbols, colours, labelling and layout types, serialisable to and from QGIS style JSON | ✅ Active |
| `qgis-sdk` (Rust core) | Native helpers behind the Python SDK: `qgis_sdk._core` + the `qgis-sdk`/`qgis-sdk` CLIs (`crates/qgis-sdk`) | ✅ Active |
| `qgis-py` (Rust core) | PyO3 module `qgis_py._core` (`py-packages/qgis-py/src-rust`); no CLI | ✅ Active |
| `qgis-node` (Rust core) | NAPI addon + CLI binaries shipped by the npm package (`ts-packages/qgis-node/src-rust`) | ✅ Active |
| `xtask` | Repository automation as a typed binary: the gate, the lints, the scaffolder, the release pipeline (`pixi run xtask …`) | ✅ Active |
| `qgis-sdk` (Python) | Plugin development SDK — dist at `py-packages/qgis-sdk`, PyPI/conda | ✅ Active |
| `qgis-py` (Python) | Python bindings + CLI — dist at `py-packages/qgis-py`, PyPI/conda | ✅ Active |
| `qgis-rs` (npm) | TypeScript/Node.js bindings + CLI — dist at `ts-packages/qgis-node` | ✅ Active |
| `@archont561/qgis-sdk` | QWebChannel bridge for plugin webviews — React/Vue/Svelte/Web-Components adapters (`ts-packages/qgis-sdk`) | ✅ Active |
| `@qgis/test-utils` | Scripted QWebChannel, fixtures and fast-check arbitraries shared by the TypeScript suites (`ts-packages/test-utils`) | ✅ Active, private |

## 📦 Release model

A release is an **explicit, immutable version tag** — never a side effect of merging to `main`.

```text
conventional commits on main
        │
        ▼  workflow_dispatch: "prepare release"        .github/workflows/autorelease.yml
convco derives the next SemVer ──► pixi run xtask release prepare
        │   rewrites every manifest (pixi.toml is the source of truth)
        │   regenerates CHANGELOG.md, refreshes bun.lock / Cargo.lock / pixi.lock
        ▼
chore(release): vX.Y.Z on main  +  tag vX.Y.Z
        │
        ▼  push tag                                     .github/workflows/release.yml
verify version ─► run gates ─► build ALL artifacts ─► publish, then release
```

**One version, checked everywhere.** `[workspace] version` in the root `pixi.toml` is the single
source of truth. Every crate inherits it (`version.workspace = true`), every wheel, npm package and
conda package restates it, and [`scripts/version.ts`](scripts/version.ts) fails the gate when any of
them disagrees:

```bash
pixi run version            # print it
pixi run version-check      # fail on drift (part of the CI gate and the pre-push hook)
pixi run version-set 0.3.0  # rewrite every manifest at once
```

**Builds are release-blocking; registries are not.** Every artifact is built and checksummed before a
single upload is attempted. Each registry is then tried independently and its outcome is reported in
the job summary, so a PyPI outage cannot delete a verified release:

| Target | Credential | Artifact |
| --- | --- | --- |
| [prefix.dev](https://prefix.dev/channels/@archont561/qgis-rs) | OIDC (`pixi upload`) | `dist/conda/*.conda` |
| [PyPI](https://pypi.org/project/qgis-py/) | OIDC Trusted Publishing | `dist/pypi/*` |
| [npmjs](https://www.npmjs.com/package/@archont561/qgis-node) | OIDC Trusted Publishing + provenance | `dist/npm/*.tgz` |
| GitHub Packages | workflow token (throwaway npmrc) | `dist/npm/*.tgz` |
| [crates.io](https://crates.io/crates/qgis-render) | `CRATES_IO_TOKEN` | `qgis-sys → qgis-styles → qgis-render → qgis-protocol → qgis-engine → qgis-server → qgis-mcp → qgis-cli` |
| **GitHub Release** | workflow token | everything above **+ `SHA256SUMS`** |

The GitHub Release is required and runs last: it holds the exact bytes whether or not a third-party
registry accepted its copy, so a maintainer can retry one service from the same immutable tag.

## ✅ CI

One required job, and it runs one command:

```bash
pixi run ci     # == xtask ci (crates/xtask), the same code GitHub Actions runs
pixi run gates  # the same gate without the coverage producers (pre-push hook)
```

`ci.yml` therefore owns only toolchain setup and caching — pixi environments, cargo registry +
`target/`, and the turbo task cache, each keyed on its own lockfile. Everything else is a
subcommand of `crates/xtask`, so "green locally" and "green in Actions" cannot mean different
things.

The gate, in order (cheap failures first):

1. `taplo` + `actionlint` on the manifests and workflows
2. `turbo run lint` — biome, `cargo fmt --check`, clang-format, clippy, clang-tidy
3. format-drift gate — `turbo run format`, then fail on a dirty tree
4. `turbo run test` — the Rust workspace under cargo-nextest (plus doctests and the C++ GoogleTest suite), both Python distributions, the NAPI addon, the bridge
5. `turbo run pack:check` — each publishable package really contains what its `files` list claims
6. `turbo run coverage` — Rust lcov + Python Cobertura XML into `target/coverage/`, uploaded to Codecov

**What was removed, and why it was safe.** The workflow used to also set up a second Python, a rustup
toolchain with `llvm-tools-preview`, a virtualenv, `pip install maturin pytest pytest-cov`, and then
run `maturin develop` + `pytest` twice by hand — after turbo had already built the same crates.

| Removed | Because |
| --- | --- |
| `actions/setup-python` | pixi's `default` env already carries the interpreter QGIS was compiled against (3.12.*); a second one is how a wheel gets built for one ABI and imported by another |
| `dtolnay/rust-toolchain` + `llvm-tools-preview` | conda-forge's `rust` ships cargo *and* a version-matched `llvm-profdata`/`llvm-cov` in its sysroot — all `cargo-llvm-cov` shells out to |
| `python -m venv` + `pip install …` | see below |
| per-package `maturin develop` / `pytest` steps | folded into the turbo graph |
| `Swatinem/rust-cache` | it shells out to `cargo`, which lives inside the pixi env here, not on the runner PATH; a plain keyed `actions/cache` does the same job |

The sandbox publish-plan check runs in its own workflow, not in this one: it needs no environment, so
it reports a broken publish contract in under a minute instead of queueing behind a native build.

### Do you need a separate venv step? No.

`maturin develop` is the only thing that ever wanted one — and the pixi `default` environment
already *is* an activated environment: it exports `CONDA_PREFIX`, which maturin accepts as the
install target, and it is the interpreter QGIS was compiled against, so a venv layered on top would
only hide QGIS's own `site-packages`.

So [`py-packages/qgis-py/package.json`](py-packages/qgis-py/package.json) runs `maturin develop
--release` (installs, and drops the compiled `_core` next to the mixed-layout Python sources that
pytest actually imports) followed by `maturin build --release --out dist` for the shippable wheel —
one cargo compilation, reused:

```jsonc
// py-packages/qgis-py/package.json
"build": "pixi run -e default bash -c 'rm -rf dist && maturin develop --release && maturin build --release --out dist && python -c \"import qgis_py._core\"'"   // builds dist/*.whl AND installs it
"test":  "pixi run -e default env QGIS_REQUIRE_NATIVE=1 python -m pytest tests -v"   // turbo: test dependsOn build
```

One compile instead of two, and CI no longer repeats per package what turbo already did.

## 🗂️ Automation: `xtask`, not `scripts/`

Everything a human, a hook or CI does to the **repository as a whole** is a subcommand of
[`crates/xtask`](crates/xtask), reached through one pixi task:

```bash
pixi run xtask ci [--no-coverage]            # the gate
pixi run xtask check-cpp [files...]          # clang-format on the native manager
pixi run xtask format-cpp                    # clang-format writes for the native manager
pixi run xtask clang-tidy                    # clang-tidy, discovering its own include paths
pixi run xtask check-sources                 # no source file hidden by .gitignore
pixi run xtask check-boundaries              # manifests obey D13 product boundaries
pixi run xtask lint-toml  [files...]         # taplo canonicality
pixi run xtask pack-check <dir> <required…>  # the published tarball has what `files` promises
pixi run xtask api-manifest [--check] [--diff-against PATH] # validate/generate API coverage
pixi run xtask scaffold <operation> <handler>
pixi run xtask setup-qca
pixi run xtask release <step>
```

A bash file that four manifests call by path is a dependency none of them can type-check: its
arguments are documented only in a comment, nothing tests it, and the day it grows a `case`
statement it is a program written in the one language in this repository with no compiler. A
subcommand is parsed by clap, compiled by the cargo this project already needs, linted by clippy and
covered by `cargo test -p xtask` — the gate lints itself. See
[`D10-xtask-over-shell-scripts.md`](.knowledge/decisions/D10-xtask-over-shell-scripts.md).

What xtask deliberately does **not** own: per-package `build` / `test` / `lint` / `format` /
`coverage`. Those stay in each package's own `package.json`, fanned out by turbo, so the command
that builds a package is in the manifest a reader of that package already has open.

**Every one of them is a single line.** `pixi run` preserves the caller's working directory, which
for a turbo task is the package's own directory, so a package verb needs no `cd` and no wrapper to
find the repository root:

```jsonc
// crates/package.json — the whole Cargo workspace as one package
"test": "pixi run -e default setup && pixi run -e default cargo nextest run --workspace --no-default-features --test-threads=1"
```

The runner is [**cargo-nextest**](https://nexte.st/), not `cargo test`: one process per test, so a
test that aborts the process — Qt does, given the wrong order — names itself instead of taking its
whole binary down, and the report is one line per test rather than per binary. The verb chains four
runs: the workspace with `--no-default-features` (**247 tests**, every QGIS-free crate), then
`qgis-sys` + `qgis-mcp` with their `qgis` features (**22 tests**, whose suites are
`#![cfg(feature = "qgis")]` and were invisible to the gate before), then `cargo test --doc` for the
four crate-level examples — nextest does not run doctests — and finally `xtask test-cpp`, the native
manager's own GoogleTest/RapidCheck suite (**14 cases**) under ctest. `QGIS_PLUGINPATH` is declared
in `[feature.py-runtime.activation.env]`, which is what let the `--fast` / `--full` split and its
two cargo invocations collapse into this one verb. The only verbs that are not one command are the
two that have to *discover* something — the clang-tidy include paths and the clang-format file set —
which is why they are subcommands above rather than shell one-liners.

### Testing just what you changed

`pixi run gates` is the pre-push gate, not the inner loop: it rebuilds wheels and the NAPI addon and
takes minutes. While working, run the narrowest thing that can still go red — then the gate once,
before you push.

```bash
# Rust — one crate, or one crate and everything that depends on it
pixi run -- cargo nextest run -p qgis-protocol
pixi run -- cargo nextest run -E 'rdeps(qgis-protocol)'   # 130 tests: the crate + its dependents
pixi run -- cargo nextest run -E 'test(bridge)'           # by test name, across the workspace
pixi run -- cargo nextest run -p qgis-sys --features qgis-sys/qgis -E 'binary(/native_manager/)' --test-threads=1

# Python — one file, one test, or one marker
pixi run -e default python -m pytest py-packages/qgis-sdk/tests/test_bridge_contract.py -q
pixi run -e default python -m pytest py-packages/qgis-sdk/tests -k handle -q

# TypeScript — one file
pixi run -- bun test ts-packages/qgis-sdk/tests/bridge-contract.test.ts

# Everything downstream of what you have already committed, and nothing else
pixi run -- bun x turbo run test --filter='...[HEAD^1]'
pixi run -- bun x turbo run test --filter=@archont561/qgis-sdk   # one package and its dependencies
```

On a machine without crates.io (the offline sandbox, see
[env-provisioning](.knowledge/env-provisioning.md)), prefix a bare turbo run with
`CARGO_NET_OFFLINE=true` and `--env-mode=loose`: the `qgis-rs` npm package builds a NAPI addon, and
`napi build` otherwise reaches for the registry. `pixi run gates` already does this for you — it is
`xtask ci --offline`.

`rdeps()` is the one worth remembering: nextest's filter expressions understand the crate graph, so
`rdeps(qgis-protocol)` is literally "the tests that could be broken by this change". Turbo's
`...[HEAD^1]` does the same for packages, but note that **every Rust crate is one turbo package**
(`@qgis/rust`), so a change anywhere under `crates/` selects the whole Cargo workspace — inside
`crates/`, reach for `-p` or `-E` instead. Turbo also caches: a second `turbo run test` with nothing
changed replays the previous result instead of re-running it, which is why `--force` appears in CI
measurements but should not appear in yours.

The shell that remains, and why ([`scripts/README.md`](scripts/README.md)):

| Script | Called by | Why still shell |
| --- | --- | --- |
| `version.ts` | `pixi run version[-check\|-set]` | the one tool that rewrites every manifest — JSON, TOML and YAML; `xtask release` calls it rather than reimplementing it |

(`scripts/restore.sh` is generated by `pixi sandbox init` and is never edited.)

## Documentation

- **[Getting Started](https://archont561.github.io/qgis-rust/getting-started/introduction/)** — installation and first steps
- **[Core Concepts](https://archont561.github.io/qgis-rust/concepts/architecture/)** — architecture and design principles
- **[Guides](https://archont561.github.io/qgis-rust/guides/rendering-projects/)** — practical tutorials
- **[API Reference](https://archont561.github.io/qgis-rust/reference/)** — complete API documentation
- **[Knowledge Base](.knowledge/)** — design documents and decision records

## Performance

> [!NOTE]
> This section used to carry a table of render/tile/iteration timings with no benchmark behind
> them: no harness in the repository produced those numbers and nothing re-measures them, so they
> have been removed rather than left to age. A reproducible benchmark — committed inputs, a
> `pixi run` verb, numbers regenerated on demand — is tracked by
> [TASK-22](backlog/tasks/task-22%20-%20Replace-the-stale-README-benchmark-table-with-a-reproducible-benchmark.md),
> and this section will quote it when it exists.

What *is* measured today is correctness, not speed: `pixi run gates` runs 247 + 22 Rust tests, 4
doctests, 14 C++ cases, 190 Python tests across the two distributions and 95 Bun tests, and the
cross-language golden vectors in `test-fixtures/` keep Rust, Python and TypeScript answering
identically.

## Comparison

| Feature | qgis-rs | PyQGIS | GeoServer | QGIS Server |
|---------|---------|--------|-----------|-------------|
| **Language** | Rust | Python | Java | C++ |
| **Performance** | ⚡ Native | 🐢 Slow | ⚡ Fast | ⚡ Fast |
| **QGIS Styling** | ✅ Full | ✅ Full | ❌ SLD only | ✅ Full |
| **Deployment** | 📦 Single binary | 🐍 Python env | ☕ JVM | 🔧 Complex |
| **Thread Safety** | ⚠️ !Send+!Sync | ❌ GIL | ✅ Yes | ❌ No |
| **Memory Safety** | ✅ Compile-time | ⚠️ Runtime | ⚠️ GC | ❌ Manual |

## Roadmap

### v0.1–v0.2 (current)
- [x] Native QGIS manager behind one C ABI, replacing the per-type CXX bridges ([D12](.knowledge/decisions/D12-qgis-native-manager-over-c-abi.md))
- [x] QgsApplication lifecycle and owner-thread shutdown
- [x] QgsVectorLayer: open, info, close, batched features, field schema
- [x] Rendering pipeline — `render_map` and `export_features` answering from real QGIS
- [x] One wire protocol for every binding, one-command gate, one-tag release model
- [x] Cross-language bridge test contract with shared fixtures
- [ ] Geometry operations (QgsGeometry)
- [ ] Generated API manifest and manager handlers (TASK-30)

### v0.3
- [ ] High-level `qgis-render` API
- [ ] Tile generation and the expression engine
- [ ] HTTP server (`qgis-server`), WMS/WFS/OGC APIs, tile caching

### v1.0
- [ ] Stable API and complete QGIS coverage (80% of classes)
- [ ] Production documentation

See [ROADMAP.md](.knowledge/ROADMAP.md) for detailed plans.

## 🤝 Contributing

Contributions are welcome! See [AGENTS.md](AGENTS.md) for repository conventions, open an issue for
bugs or feature requests, and submit changes through a pull request. Commits follow
[Conventional Commits](https://www.conventionalcommits.org/) — `convco` enforces it in the
`commit-msg` hook, and the changelog is generated from that history rather than edited.

### Development setup

```bash
git clone https://github.com/Archont561/qgis-rust.git
cd qgis-rs

# Install the two environments and the Bun workspace
pixi install -e default -e bun
pixi run bun-install

# Install the git hooks (format, clippy, conventional commits, the gate on push)
pixi run -e default lefthook install

# The complete local gate — the same file CI runs
pixi run ci

# The pre-push gate, without the coverage producers
pixi run gates

# While working: just the affected tests (see "Testing just what you changed")
pixi run -- cargo nextest run -E 'rdeps(<the crate you touched>)'

# Repo-wide agent tools
pixi run skills
pixi run backlog task list --plain
```

Two pixi environments, and the split is forced by conda-forge: `qgis` needs `icu >=78.3` while `bun`
needs `icu >=75.1,<76`, so a single environment carrying both does not solve. `default` holds QGIS,
Rust, the C++ toolchain and Python; `bun` holds Bun (and Rust, because `napi build` shells out to
cargo). See [D08](.knowledge/decisions/D08-icu-split-and-bun-toolchain.md).

#### Dev container (Pixi + OpenCode)

In VS Code, run **Dev Containers: Reopen in Container**. The container uses the
[official Pixi image](https://github.com/prefix-dev/pixi-docker) (v0.81.0) and has no Node.js
toolchain; on creation it installs `opencode-ai` with bun for the non-root `vscode` user. No provider
credentials are required or stored in this repository — run `opencode auth login` interactively.

The large QGIS/Rust environment is **not** installed automatically:

```bash
pixi install -e default -e bun
pixi run bun-install
pixi run ci
```

### Building documentation

```bash
# Dev server at http://localhost:4321/qgis-rs
pixi run -e bun bun x turbo run dev --filter=qgis-rs-docs

# Production build
pixi run -e bun bun x turbo run build --filter=qgis-rs-docs
```

The site lives in [`docs/`](docs/) and is published to
[archont561.github.io/qgis-rust](https://archont561.github.io/qgis-rust/) by
[`docs.yml`](.github/workflows/docs.yml) after a green CI run on `main`. See
[`docs/README.md`](docs/README.md) for the one-time Pages setup.

## License

Licensed under the [GNU General Public License v2.0 or later](https://spdx.org/licenses/GPL-2.0-or-later.html),
consistent with the workspace package manifests.

## Acknowledgments

- [QGIS](https://qgis.org/) — the amazing open-source GIS platform
- [CXX](https://cxx.rs/) — safe FFI between Rust and C++
- [Pixi](https://pixi.sh/) — fast, modern package management
- [Astro Starlight](https://starlight.astro.build/) — documentation theme

## Support

- **Issues**: [GitHub Issues](https://github.com/Archont561/qgis-rust/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Archont561/qgis-rust/discussions)

---

<p align="center">
  Built with ❤️ by the qgis-rust community — <a href="https://github.com/Archont561/qgis-rust">⭐ star us on GitHub</a> if you find this useful.
</p>
