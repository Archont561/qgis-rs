# Bundle Update Log

## 2026-09-18

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
