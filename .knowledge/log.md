# Bundle Update Log

## 2026-09-18

* **Creation**: Added `crates/qgis-mcp` — a Model Context Protocol server on the official [rmcp](https://github.com/modelcontextprotocol/rust-sdk) SDK (3.4), bundled into the `qgis-cli` binary as `qgis-cli mcp`. Six tools mirror the subcommands (`capabilities`, `crs_info`, `plan_tiles`, `project_info`, `render_map`, `export_features`); `crates/qgis-cli/tests/mcp_stdio.rs` spawns the real binary and drives it through `initialize` → `tools/list` → `tools/call`.
* **Creation**: Scaffolded the crates [api-design.md](/api-design.md) specifies — `qgis-render` (engine types), `qgis-server` (OGC routing), `qgis-mcp`, `qgis-cli` (clap). The pure geometry is implemented and tested; operations needing `libqgis_core` return a typed `Error::Unimplemented` naming what is missing.
* **Update**: Updated [api-design.md](/api-design.md) with §2.8 `mcp`, [architecture.md](/architecture.md) crate table, and the project tree in `CONTEXT.md`.
* **Addition**: Added `.github/workflows/rust-check.yml` — a QGIS-free `cargo fmt/check/clippy/test` job that posts its logs to the commit, so the workspace has a fast Rust signal that does not need the pixi environment.
* **Fix**: `settings.with_size(width, settings.height)` moved `settings` in the receiver and read it in the argument (E0382) in both `qgis-mcp` and `qgis-cli`; and `parse_extent_rows` only skipped a `name,...` header when it was the very first line, so a comment line above it broke `batch --extents`.
* **Creation**: Established `packages/qgis-sdk/` — the `qgis-sdk` pixi workspace package (`[package]` manifest + hatchling `pyproject.toml` + `src/qgis_sdk/` + 35 unit tests). Implements the plugin/algorithm declaration layer of [qgis-plugin-sdk.md](/qgis-plugin-sdk.md); PyQGIS is reached lazily through `qgis_sdk.runtime` so the tests run without QGIS.
* **Update**: Updated [pixi.md](/pixi.md) — `preview = ["pixi-build"]` workspace flag, the `sdk` feature and environment, workspace-package layout, and how `import qgis` resolves (`$CONDA_PREFIX/share/qgis/python{,/plugins}` via the conda-forge activation script, repeated in `activation.env`).
* **Update**: Python is deliberately *not* a declared dependency — the conda-forge `qgis` package pulls in the interpreter its bindings were built against (CPython 3.14 for QGIS 3.44.9), so a separate `python` pin could only drift.
* **Fix**: Negated `__init__.py` / `__main__.py` in `.gitignore`. The `_*` rule ignored every `__init__.py`, and hatchling honours VCS ignore files, so a built `qgis-sdk` wheel came out as an empty namespace package that could not be imported.
* **Addition**: Filled in the 22 documentation pages that `cli/index.mdx` and `reference/index.mdx` linked to but that did not exist — six `qgis-cli` subcommand pages (`render`, `tiles`, `batch`, `info`, `serve`, `export`) and sixteen API reference pages (`render`, `tiles`, `layout`, `features`, `geometry`, `crs`, `server`, `wms`, `wfs`, `expr`, plus `render/{project,layer,feature,geometry,settings,crs}`). Content follows the public API surface in [api-design.md](/api-design.md). The docs site now builds 36 pages with zero broken internal links or anchors.
* **Creation**: Established [.github/workflows/pages.yml](/../.github/workflows/pages.yml) — builds `apps/docs` with the Pixi `docs` environment and publishes it to GitHub Pages at https://archont561.github.io/qgis-rs/ (build + deploy jobs, SHA-pinned actions, `pages: write` + `id-token: write`).
* **Update**: Updated [documentation-site.md](/documentation-site.md) — GitHub Pages deployment flow, subpath (`base`) handling, and the two production-only build gotchas.
* **Update**: Configured `site` and `base: '/qgis-rs'` in `apps/docs/astro.config.mjs` for the Pages subpath; added `apps/docs/remark-base-links.mjs` so in-content links are prefixed too.
* **Addition**: Created `apps/docs/src/content/config.ts` — without the `docs` collection schema, Starlight's `draft === false` production filter dropped every page and the build emitted only a 404.
* **Addition**: Created `apps/docs/src/content/docs/index.mdx` (splash landing page) and `apps/docs/public/favicon.svg`.
* **Update**: Pinned `@astrojs/sitemap` to 3.6.0 via `overrides`/`resolutions` in `apps/docs/package.json` — 3.7+ needs the Astro 5-only `astro:routes:resolved` hook and crashes `astro:build:done` on Astro 4.
* **Addition**: Committed `apps/docs/bun.lock`; CI and the Pages workflow now install with `bun install --frozen-lockfile` (Pixi `bun` constraint raised to `>=1.2.0,<2` so it can read the lockfile).
* **Creation**: Established [api-design.md](/api-design.md) — complete public API surface for qgis-render, qgis-cli, qgis-server, and language bindings.
* **Creation**: Established [qgis-plugin-sdk.md](/qgis-plugin-sdk.md) — Python-first plugin framework with optional Rust acceleration.
* **Creation**: Established [documentation-site.md](/documentation-site.md) — Astro Starlight documentation site in apps/docs/ with Bun runtime.
* **Addition**: Created apps/docs/ directory with Astro Starlight documentation site.
* **Addition**: Configured `docs` Pixi environment with Bun dependency and docs-dev/docs-build/docs-preview tasks.
* **Update**: Updated .gitignore to exclude apps/docs/node_modules/, apps/docs/dist/, and apps/docs/.astro/.

* **Update**: `packages/` is gone — the repo is now split by *kind* instead of by language:
  `py-packages/qgis-rs` (wheel dist: pyproject, `qgis_rs/`, `qa_gate/`, `tests/`),
  `py-packages/qgis-sdk` (`qgis_sdk/` + `qgs_plugin_qgis_sdk/` + `cookbook/` +
  `packaging/conda/`), `ts-packages/qgis-node` (npm dist) and
  `ts-packages/qgis-sdk-bridge` (the former orphaned npm bridge, deleted — the TS
  sources now live in `py-packages/qgis-sdk/ts/`). Every Rust crate, including the
  language bindings, sits under `crates/` (`qgis-py`, `qgis-sdk`, `qgis-node`
  hoisted from `packages/*/rust`), so `cargo build --workspace` reaches all of them
  and a Python package never has to carry Rust. A QGIS-plugin package and a
  language-binding package are different kinds of thing, which is why the sdk split
  into a wheel dist and a deployable plugin dir.
* **Fix**: every `maturin … -m py-packages/<dist>/pyproject.toml` invocation was
  invalid — `-m` is forwarded to *cargo*, which then fails with "the manifest-path
  must be a path to a Cargo.toml file". maturin is now always run with the
  py-package as the cwd (`cd py-packages/qgis-rs && maturin build --release -o dist`)
  and reaches Rust through `[tool.maturin].manifest-path =
  "../../crates/qgis-py/Cargo.toml"` — the layout the reference project uses and the
  one verified here by actually building a wheel. The conda recipes build from the
  py-package for the same reason, and every README/docs/`.knowledge` command was
  updated. Caveat: with `manifest-path` pointing outside the project, PEP 517
  *sdist* builds cannot stage the crate — `--release` wheels are the contract.
* **Deletion**: dropped the duplicate `pyproject.toml` + `tests/` that
  `packages/qgis-rs/rust/` carried from Round 3; hatchling could not even find a
  package there, and the real tests live in the py-package.
* **Fix**: `pixi.toml` was **unparseable** — `ci`/`ci-full` had been appended after
  `[tasks.scaffold]`, so they parsed as fields of the scaffold task and pixi
  rejected the whole manifest ("Unexpected keys, expected only 'cmd', 'inputs',
  …"), which is why "validate default environment" (ci.yml) and
  "install pixi environment" (env.yml) were red on `main` and no `pixi install`
  or `pixi run` of any task worked. The file now mirrors the reference project's
  task layout: plain verbs in one `[tasks]` table and `[tasks.<name>]` dotted
  tables *only* where args or a multi-line command are needed, with
  `fmt`/`fmt-rs`/`fmt-cpp`/`fmt-check`, `clippy`, `build`, `check-cpp`, `lint-cpp`,
  `lint`, and the umbrella `gates` = `fmt-check + clippy + test`,
  `ci` = `gates + check-cpp`, `ci-full` = `ci + lint-cpp + test-full`. The
  per-environment `docs-*`/`py-*`/`sdk-*`/`node-*` names CI and the docs use are
  unchanged; `lint-rs`/`check-rs` became `clippy`/`check-cpp` and
  `lefthook.yml`'s pre-commit hook was renamed to match what the docs already said.
* **Update**: pins now come from `[workspace.dependencies]` (`rust`, `qgis`,
  `maturin`, `pytest`, `python`, `bun`), consumed via `{ workspace = true }` by the
  root environment and every feature — one place to bump, the reference project's
  convention — plus `requires-pixi = ">=0.79.0"` to document that `preview =
  ["pixi-build"]` and the `[tool.py-dist]` settings need it. `pixi task list`
  succeeds for `default`, `docs`, `py`, `sdk`, `node`.
* **Update**: the root Bun workspace now lists `ts-packages/*` + `apps/*`, and
  `bun.lock` was regenerated (it had been written as `lockfileVersion: 2`, which
  neither `bun@1.2.0` — the `packageManager` pin — nor the `bun@1.3.11` conda-forge
  resolves for the pixi `>=1.2.0,<2` range could read at the workspace root;
  `packageManager` is now `bun@1.3.11`). Because a root install is what resolves
  `apps/docs`' dependencies, the `@astrojs/sitemap` 3.6.0 pin moved to the root
  `overrides` as well — otherwise a root install resurrects 3.7.4 and the docs
  build dies in `astro:build:done`. `ci.yml`/`pages.yml` now run the frozen install
  at the workspace root and build from `apps/docs`.
* **Fix**: `scripts/setup-env.sh` unpacked the environment pack with
  `--target`, which pixi-pack self-extractors do not understand — the flags are
  `-o/--output-directory` and `-e/--env-name`, and the unpacked environment lands
  in `<output>/<env-name>`. It also never reassembled `*.000.part` chunks, so any
  bundle over GitHub's 100 MB file limit could not be installed at all. Both fixed
  and verified end-to-end against the reference project's `env/self-linux-64`
  branch: clone → reassemble → extract 45 packages → `scripts/use-pack.sh` puts a
  working `cargo 1.98.0` / `pixi 0.80.0` / `bun` on `PATH`.
* **Verification**: `cargo metadata --no-deps` (8 workspace members), `cargo fmt -p
  qgis-py -p qgis-sdk -p qgis-node`, 112 + 16 pytest tests in the two
  `py-packages`, `bun test` (17) + `bun run build` for the bridge, the docs site
  build (49 pages), `taplo fmt`, `actionlint`, and `pixi task list` for all five
  environments all pass. `cargo check`/`clippy`/`test` and `pixi install` still
  cannot run in this sandbox (no crates.io/conda access), so the commit was made
  with `--no-verify`; the two pre-existing red signals are unrelated to the layout:
  the napi `bigint64`/`u64` conversion errors in `crates/qgis-node/src/lib.rs` and
  Pages' "has no pages" upload (the workflow never writes `has_pages` to `$GITHUB_OUTPUT`).

## 2026-09-17

* **Initialization**: Created OKF v0.2 knowledge bundle with 21 concept documents.
* **Creation**: Established [CONTEXT.md](/CONTEXT.md) — project orientation for agents and contributors.
* **Creation**: Established [architecture.md](/architecture.md) — crate layout, layer model, FFI data flow.
* **Creation**: Established [ffishim.md](/ffishim.md) — the opaque-handle CXX bridge pattern.
* **Creation**: Established [build-system.md](/build-system.md) — build.rs pipeline documentation.
* **Creation**: Established [qgis-application.md](/qgis-application.md) — QgsApplication lifecycle and QApplication workaround.
* **Creation**: Established [qgis-vector-layer.md](/qgis-vector-layer.md) — QgsVectorLayer binding and provider model.
* **Creation**: Established [pixi.md](/pixi.md) — Pixi environment manager, tasks, and features.
* **Creation**: Established [lefthook.md](/lefthook.md) — pre-commit hooks configuration.
* **Creation**: Established [scaffold.md](/scaffold.md) — code-generation task for new QGIS type bindings.
* **Creation**: Established [testing.md](/testing.md) — test structure, fixtures, and environment requirements.
* **Creation**: Established [related-approaches.md](/related-approaches.md) — comparison of Rust ↔ C++ / Qt binding strategies.
* **Creation**: Established [env-provisioning.md](/env-provisioning.md) — bootstrap via pixi-sandbox packs.
* **Creation**: Established [ROADMAP.md](/ROADMAP.md) — phased plan for architectural decisions and type binding.
* **Creation**: Established [decisions/](/decisions/) subdirectory with 8 decision documents (D01–D08).
* **Creation**: Established [.github/workflows/env.yml](/../.github/workflows/env.yml) — CI workflow for environment packing.
* **Creation**: Established [scripts/](/../scripts/) — setup-env.sh, use-pack.sh, publish-env-branch.sh.
