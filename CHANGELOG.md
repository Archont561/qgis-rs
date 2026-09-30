# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to
[Conventional Commits](https://www.conventionalcommits.org/).

## v0.1.0 (2026-09-30)

### Features

* **dev:** turborepo orchestration, repo-wide gates, one-call pixi ci with caching, codecov, and
docs gated on green CI
([a5e7760](https://github.com/Archont561/qgis-rs/commit/a5e7760101829ba8f12604f60908ee94aa34bc4c))
* **qgis-sdk:** add declarative APIs and integration coverage
([d4d4668](https://github.com/Archont561/qgis-rs/commit/d4d46686393c492a434caae0d994cd91d78f53bf))
* **env:** python in dev, pytest-cov in py, bun-driven JS tests (#10)
([b683d05](https://github.com/Archont561/qgis-rs/commit/b683d05f0a1b1ce59ec02d021ad1eac5699233ed)),
closes [#10](https://github.com/Archont561/qgis-rs/issues/10)
* **sdk:** Phase 0-3 — Qt funnel, qgis-styles IR, provider registration, metadata keys
([7a0a822](https://github.com/Archont561/qgis-rs/commit/7a0a8222ebf6305108623f04bcdd26c22fec1fde))
* complete refactor plan - split py/bun/rs, declarative API, QGIS Web API, docs
([6a993a0](https://github.com/Archont561/qgis-rs/commit/6a993a072a81b4fc740003364a0765333e7d3061))
* declarative plugin + self-install bootstrap + bun bridge + complete QGIS Web API
([60e8210](https://github.com/Archont561/qgis-rs/commit/60e82105178e79df5ec44f672311982c59b9131d))
* **qgis-sdk:** requests-like network, celery-like tasks, fixtures, docs, scaffold + refactor plan
with self-installing runtime
([73b811e](https://github.com/Archont561/qgis-rs/commit/73b811e61a5088dd130fbf5c34ae9cc40ea8c81c))
* **cli:** bundle a qgis-mcp server in qgis-cli, scaffold the crate tree
([0ac1b31](https://github.com/Archont561/qgis-rs/commit/0ac1b312154284a6eeb3b22426ed118873553c00))
* **sdk:** add the qgis-sdk pixi workspace package
([4a27d60](https://github.com/Archont561/qgis-rs/commit/4a27d601798c81a5324ed4cf6b32a87f34518d2e))

### Fixes

* **test:** qualify NetworkManager in test_network_manager_fallback
([49a953b](https://github.com/Archont561/qgis-rs/commit/49a953bc94d3e02105229cd44f3827efbbc23472))
* **publish:** disable setup-pixi cache
([d1e2362](https://github.com/Archont561/qgis-rs/commit/d1e2362b67243f9b07ef4dea78557670d77ee73b))
* **ci:** upgrade pixi-sandbox to v0.3.2
([37ccb8c](https://github.com/Archont561/qgis-rs/commit/37ccb8c152d59e51e5fa3040f36d625de854ae8b)),
closes [#37](https://github.com/Archont561/qgis-rs/issues/37)
* **ci:** reference the pixi-sandbox action at the repo root, not its shims
([a0b1280](https://github.com/Archont561/qgis-rs/commit/a0b12804ce7771d944f44f940dcddd53b2708c9b))
* **ci:** build the SDK bridge from its own task, not the root one
([b11ba64](https://github.com/Archont561/qgis-rs/commit/b11ba647629fbe400439be945deb90461a0a157c))
* **publish:** disable cache in Install Pixi to avoid manifest lookup failure (#9)
([aed2c2f](https://github.com/Archont561/qgis-rs/commit/aed2c2f20e5c9b863531f4690c1ac486643cf4f2)),
closes [#9](https://github.com/Archont561/qgis-rs/issues/9)
* **publish:** strip schema from plan matrix for GitHub strategy.matrix (#8)
([44922c8](https://github.com/Archont561/qgis-rs/commit/44922c8d572e96bf29b1b0de2a7ae7f27c81cd97)),
closes [#8](https://github.com/Archont561/qgis-rs/issues/8)
* **node:** name the test file instead of globbing it
([da0809f](https://github.com/Archont561/qgis-rs/commit/da0809f30b55437f1ecb041c07fb7a3bf0758b9f))
* **node:** cross tile and byte counts as i64, and test the package for real
([0ca8e03](https://github.com/Archont561/qgis-rs/commit/0ca8e03f1879c012ffcb8b9aaa1d9523a41f9b0d))
* **env:** give pixi.toml the reference project's `pack` verb and its tooling
([b6763fd](https://github.com/Archont561/qgis-rs/commit/b6763fdb5b4e1c62f717a5b619ef73309089bd19))
* **ci:** create a virtualenv before 'maturin develop'
([1b4ec52](https://github.com/Archont561/qgis-rs/commit/1b4ec52f45ef9dfdbc22b8b6b827e3119c359922))
* **pixi:** drop invalid default-environment key from the docs-build task
([70a7f08](https://github.com/Archont561/qgis-rs/commit/70a7f0833f0ba9813e9bbffd64dfda1332c2fd15))
* **cli:** skip the extents header wherever it appears, document the mcp surface
([2d9f8c9](https://github.com/Archont561/qgis-rs/commit/2d9f8c9c72fbc630d2092414b82de5ba4c92c867))
* **cli:** read the render size before consuming the settings
([bcaacc5](https://github.com/Archont561/qgis-rs/commit/bcaacc5e377f72e2346e4efe865332779e2e6940))

### Refactoring

* **env:** collapse six pixi environments into `default` and `bun`
([cab1b87](https://github.com/Archont561/qgis-rs/commit/cab1b87d904bd699413096e0e5adac4e3bef0cb5))
* split packages/ into py-packages/, ts-packages/ and crates/
([c569e12](https://github.com/Archont561/qgis-rs/commit/c569e12f3cabe8f18cca36d3e6aebd577af3c2b7))

### Documentation

* **knowledge:** record the CI-shape fixes found from step results
([21c983b](https://github.com/Archont561/qgis-rs/commit/21c983b804336fe646f22a660c50af3fdc9c3cee))
* **knowledge:** record the boundary fix, the test runner swap and the lockfile cleanup
([c1638d6](https://github.com/Archont561/qgis-rs/commit/c1638d60e6eef837387a885f63f38fa5788a4229))
* refactor plan — use bun instead of node, add complete QGIS Web API (qgis.*) for webview
([3f9f06b](https://github.com/Archont561/qgis-rs/commit/3f9f06b10298d394907135582009a488704e1f00))
* expand refactor plan with self-installing runtime helper for plugin zip distribution
([629d906](https://github.com/Archont561/qgis-rs/commit/629d9066239346e9ceba8bbe3db13d8298f91e81))
* point rust-check at main and record the new crates in the README
([4f06ab2](https://github.com/Archont561/qgis-rs/commit/4f06ab27f8ea130efa5433087d213d9c789f9b1f))
* **docs:** write the 22 pages the CLI and reference indexes linked to
([5e38636](https://github.com/Archont561/qgis-rs/commit/5e38636aaf07f7cbebc82a9bbcc2ad5cc9851a94))
* **docs:** drop the npm instructions, the docs env is Bun-only
([a115703](https://github.com/Archont561/qgis-rs/commit/a1157037deae86da4529566f3dd7f1d4952810b4))

### Build System

* **repo:** script every long task, move docs to /docs, adopt the geoquery release model (#17)
([3ee2f02](https://github.com/Archont561/qgis-rs/commit/3ee2f02b1db5ae0f12cc5596d1c3ea02b3a06eca)),
closes [#17](https://github.com/Archont561/qgis-rs/issues/17)
* **dev:** own the cargo test tooling in pixi, drop the CI cargo install
([0c3d8ad](https://github.com/Archont561/qgis-rs/commit/0c3d8ad2907f878568821b1c8a2c087dda42ce27))

### CI

* validate sandbox plan before native tests
([b7b04b2](https://github.com/Archont561/qgis-rs/commit/b7b04b24fbf8d34a2c5d6a077b8d99bb835b80fb))
* republish sandbox only when its inputs change (#11)
([84ee9a7](https://github.com/Archont561/qgis-rs/commit/84ee9a771b1cc1aa7a934e067ab0dcd7e6736588)),
closes [#11](https://github.com/Archont561/qgis-rs/issues/11)
* **rust-check:** format the moved binding crates, and only push on push events
([73d8b31](https://github.com/Archont561/qgis-rs/commit/73d8b310e5f288108817a17c8c424200ae73364c))
* **env:** mirror the reference project's unpinned pixi install
([591480c](https://github.com/Archont561/qgis-rs/commit/591480ccb21a33a27e0fc0a0546f6bca235a39df))
* **docs:** publish the docs site to GitHub Pages
([02fb02c](https://github.com/Archont561/qgis-rs/commit/02fb02c1474f4ae843212ae92dc5b48ea59e5fdf))
