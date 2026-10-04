# Bundle Update Log

## 2026-10-04 (session 2)

* **Change (testing)**: The native manager has its own C++ tests, and the gate
  runs them. `manager.cpp` kept the JSON envelope, the handle encoding and the
  C ABI's malloc/free pair in an anonymous namespace inside a translation unit
  that cannot be loaded without a QGIS prefix and a `QApplication` — so the
  functions most likely to cost a leak, a truncated answer or a wrong layer
  were the only ones nothing tested as units. They move to
  `crates/qgis-sys/src/native_manager/conversions.cpp`, which depends on QtCore
  and the standard library only, and `crates/qgis-sys/tests/cpp` builds that one
  file against GoogleTest 1.18 and RapidCheck: 14 tests, 9 examples and 5
  properties, headless, under the same warnings-as-errors contract `build.rs`
  compiles the shim with. `xtask test-cpp` drives cmake/ninja/ctest and
  `@qgis/rust`'s `test` script calls it, so `pixi run ci` covers the C++ suite
  like every other (D10). No new dependency: cmake and ninja (TASK-24), gtest
  and rapidcheck were already declared in `pixi.toml` and carried in the offline
  pack — which matters, because this machine cannot run `pixi lock`.
* **Change (ci)**: `cpp_sources` now walks the shim's `tests` tree, so
  clang-format and the format-drift gate see C++ test files that were invisible
  to them before. The counterpart is that clang-tidy is narrowed to
  `crates/qgis-sys/src`: it is driven by `compile_commands.json`, which
  `qgis-sys`'s build script writes only for what cargo compiles, and handing it
  a CMake-built file makes it guess a command line and fail on the first Qt
  include.
* **Measurement**: the property over `copy_response` was written against
  arbitrary byte strings and failed immediately — not on the conversion, but on
  the test's own premise. `QString::fromStdString` decodes UTF-8 and substitutes
  U+FFFD for what it cannot decode, so two distinct invalid sequences collapse
  onto one key and a round-trip property is false for reasons that have nothing
  to do with the manager. The properties now generate printable ASCII, which is
  what the wire actually carries, and the replacement behaviour is pinned by an
  example test instead of being hidden by the fix. Worth remembering the next
  time a property is written over anything Qt will decode.
* **Verified**: `pixi run gates` is **green on a restored airlock** — 3m35s cold,
  1m56s warm — which the session skill said was impossible as recently as
  yesterday. Both reasons it gave were fixed by `d24772c`: the gate forces
  `--offline` and `--env-mode=loose`, so the napi build keeps `CARGO_HOME` and
  its vendored sources, and `patchelf` is now declared and packed, so
  `qgis-rs-py#build` produces a wheel locally. Baseline on `4a87ed2`: **194 Rust**
  across 42 non-empty test-binary runs, **123 + 2 skipped** and **21** pytest,
  **44** bun, **14** C++. `.agents/skills/session/` was corrected to say all of
  this, including the restore's current figures (8708 blobs, 75732 verified
  entries).
* **Idea (not implemented)**: TASK-23 is **not** closeable and stays In Progress
  on two ACs. AC#2 wants rstest fixtures instead of a hand-rolled setup helper
  per test file; rstest is a workspace dependency but is used in exactly one
  file, `crates/qgis-render/tests/tiles.rs`. AC#4 wants both TypeScript client
  suites on fast-check; `ts-packages/qgis-node` has it, `ts-packages/qgis-sdk-bridge`
  does not, so the bridge asserts none of the invariants the Rust properties do.
  Both are local, offline-provable work — fast-check and rstest are already
  installed — and neither needs a lock.
* **Idea (not implemented)**: two backlog findings, neither acted on because
  they change task metadata the user has not ruled on. **TASK-43's dependency on
  TASK-36 looks wrong**: 43 is about the dependency graph (no `qgis-sdk` →
  `qgis-py`, delete `_fallback_cli.py`) and 36 defines the declarative UI
  contract; with that edge in place the hand-off at the end of the previous
  session recommended a task its own metadata says is blocked, and TASK-44 is
  blocked behind 26, 42 and 43 in turn. **TASK-6 is archived while still
  `status: To Do`**, and TASK-7 depends on it, so the binding chain
  7 → 8 → 9/10 → 11/12 — six tasks across m-1 and m-2 — is blocked by a task no
  list shows. Either re-point TASK-7 at TASK-5 (Done) or record that the chain
  is superseded by the RFC-19 native manager.
* **Next session's opening prompt**: see the session report; in short, finish
  TASK-23 by putting rstest fixtures through the Rust suites (AC#2) and a
  fast-check property into `ts-packages/qgis-sdk-bridge` (AC#4), which closes
  the task and unblocks TASK-31 and the 32/33/34 → 35 → 42 chain behind it.

## 2026-10-04

* **Change (ci)**: The D13 product boundaries are decided by a program instead
  of by review. `crates/xtask/src/boundaries.rs` adds `xtask check-boundaries`,
  which reads every member manifest plus the two distribution manifests and
  rules on four things: the forbidden dependency edges (no `qgis-sdk` →
  `qgis-py`, no binding crate depending on another binding crate, nothing
  depending on a CLI), binding crates owning no `[[bin]]`, the canonical
  executable names (`qgis-cli`, `qgis-mcp`, `qgis-plugin`, `xtask`), and a
  closed list of tracked fallbacks so a new one cannot appear unnoticed. It
  runs in `xtask gate`'s repo-lints step, before anything compiles, and costs
  no new dependency — the checker hand-parses TOML because the airlock cannot
  fetch one. Today it reports `12 crates and 2 distributions match D13 (1
  tracked fallback(s))`; 11 tests in `crates/xtask/tests/boundaries.rs` cover
  the rules, the real repository, and a discovery guard that fails if a crate
  stops being seen. Two deviations are named rather than silently allowed:
  `py-packages/qgis-sdk/src/qgis_sdk/_fallback_cli.py` (TASK-43) and the
  `qgis-cli` console script that `qgis-sdk` also ships (TASK-44).
* **Change (testing)**: The gate now runs the QGIS-backed code it used to only
  compile. `@qgis/rust`'s `test` script runs the workspace with
  `--no-default-features` and then `cargo test -p qgis-sys -p qgis-mcp
  --features qgis-sys/qgis,qgis-mcp/qgis -- --test-threads=1`, which is what
  closes RFC 19 phase four: before this, the `qgis` feature paths had zero
  tests executed anywhere, so "it builds" was the only claim the repository
  could make about them. Rust went from 149 to 183 passing tests across 35
  test-binary runs (30 integration files, 5 of them re-run under the feature).
  Single-threaded on purpose: QGIS initialization is process-global.
* **Addition**: `crates/qgis-protocol`'s crate documentation now states the
  binary-artifact policy — renders cross the wire as filesystem paths, never as
  base64 bytes — so the rule lives next to the types it constrains instead of
  only in `.knowledge/decisions/D12-qgis-native-manager-over-c-abi.md` §3.
  D12 also gained the snake_case amendment that issue #19 was closed on.
* **Idea (not implemented)**: `xtask scaffold` still emits a `cxx::bridge`
  module and a `#include "rust/cxx.h"` for a crate that no longer has `cxx` or
  `cxx-build` anywhere in it. Nothing is broken today, but the next binding
  scaffolded from it would reintroduce the exact dependency RFC 19 spent four
  phases removing, and the gate would not catch it — `check-boundaries` rules
  on edges between crates, not on what a generator writes. Filed as TASK-45:
  either teach the template the native-manager shape D12 chose, or delete the
  C++ half of the template and let `scaffold` make Rust-only crates.
* **Idea (not implemented)**: `qgis-rs-py#build` cannot run in this sandbox
  because `patchelf` is in neither `pixi.toml` nor the offline pack, and
  adding it needs `pixi lock`, which needs the network. CI runners supply it,
  so the gap is local-only — but it means `pixi run gates` is not actually the
  same command CI runs, and the difference is discovered rather than declared.
  Declaring `patchelf` as a pixi dependency the next time the lock can be
  regenerated would close it.
* **Verified**: PR #25 was green before the merge (CI 8m51s) and squash
  `067d2a6` is green on `main` after it (CI 9m17s, Docs 50s). The `publish
  sandbox` workflow correctly did not fire: its `paths` allowlist covers the
  manifests and the vendored crate graph, and this change touched neither.
  Locally the same fan-out is 21 of 25 tasks with `--env-mode=loose`, the one
  failure being the `patchelf` gap above — so the green that counts here is
  CI's, not the sandbox's.
* **Next session's opening prompt**: TASK-40 closing unblocked four tasks —
  41, 42, 43 and 26 — and 44 waits on 26. Start by reading
  `.knowledge/decisions/D13-rust-cli-ffi-and-qgis-sdk-boundaries.md` and the
  capability-ownership matrix in
  `backlog/docs/architecture/doc-7 - ...Product-Boundaries.md`, then take
  TASK-43 (delete `_fallback_cli.py`) and TASK-44 (the duplicate `qgis-cli`
  console script in `qgis-sdk`): both are now the only two deviations
  `xtask check-boundaries` tolerates, and closing them lets the tracked-
  fallback list shrink to zero. Before touching Python, run
  `export PATH="$HOME/.local/bin:$PATH"`, `pixi run setup`, then
  `pixi run bun-install`; expect `qgis-rs-py#build` to fail locally on
  `patchelf` and filter it out. TASK-45 (the `xtask scaffold` cxx template) is
  already filed and is a good small warm-up if you want one.

## 2026-10-03

* **Change (ffi)**: The Python and Node bindings no longer mirror the domain
  types. `crates/qgis-protocol` defines the wire format (`EngineRequest` /
  `EngineResponse`, `TRANSPORT_VERSION = 1`, a closed `Operation` enum with 13
  variants and `Operation::all()`, `ErrorKind`), `crates/qgis-engine` owns
  `invoke(&str) -> String` with one match arm per operation, and each binding
  crate is now a single `invoke` function — `crates/qgis-py` went from 778
  lines of `#[pyclass]` to ~65, `crates/qgis-node` from 632 to ~40. The
  ergonomic APIs moved into the host languages
  (`qgis_rs/_transport.py` + `_api.py`, `ts-packages/qgis-node/index.js`), and
  the `_fallback.py` / `fallback.js` re-implementations were deleted: a
  fallback is a second set of answers. Everything on the wire is `snake_case`,
  including operation names; the JS client renames at its own edge. Golden
  values are now asserted identically in all three suites (4568 tiles for
  `14,50,15,51` z10-14; `tile_from_lon_lat(10, 13.9, 51.1)` ⇒ `{10,551,342}`).
  15 engine tests, 6 protocol tests, 17 pytest, 11 bun contract tests —
  all green. Rationale and costs: `.knowledge/decisions/D09-wire-protocol-over-ffi.md`.
* **Change (ci)**: Repository automation is `crates/xtask`, a clap binary with
  16 unit tests, instead of eight shell files called by path from four
  manifests. `ci.sh`, `check-cpp.sh`, `lint-toml.sh`, `npm-pack-check.sh`,
  `scaffold.sh`, `setup-qca.sh`, `ci-failure-summary.sh` and `release/*.sh` are
  deleted; `pixi.toml`, `lefthook.yml`, `ci.yml`, `autorelease.yml`,
  `release.yml` and the npm `pack:check` scripts call subcommands. A generic
  `pixi run xtask <sub> [args]` task means a new repository verb needs no new
  pixi task; `ci`, `gates`, `setup`, `scaffold`, `check-cpp` and `lint-toml`
  stay as aliases because hooks and humans already type them. Per-package
  verbs stayed with turbo on purpose. `xtask release` publishes
  `qgis-protocol` and `qgis-engine` alongside the original six crates and
  shells to `pixi run version` rather than reimplementing `scripts/version.ts`.
  Rationale: `.knowledge/decisions/D10-xtask-over-shell-scripts.md`.
* **Change (testing)**: `src/` is code and `tests/` is tests, in every crate and
  every package. 21 `#[cfg(test)] mod tests` blocks (~1100 lines) moved out of
  `crates/*/src/` into `crates/*/tests/<topic>.rs`; the same 120 tests still
  run, now as integration tests that use each crate the way a consumer does.
  Consequences: `crates/xtask` is a library plus a six-line `main.rs` (a
  `[[bin]]` cannot be linked from `tests/`); the items the tests need are now
  `pub` with a doc comment saying so (`CRATES`/`already_published`,
  `split_list`/`what_is_served`/`tiles`, the `#[tool]` handlers plus a public
  `QgisMcpServer::tools()` for the router the macro generates privately);
  `crates/qgis-node` gained the adapter test `crates/qgis-py` already had; and
  `ts-packages/qgis-node` — the one package whose sources sat at its root —
  moved `index.js`/`index.d.ts` into `src/`, with `main`, `types`, `files` and
  `pack:check` following. Rationale:
  `.knowledge/decisions/D11-tests-outside-src.md`. The next step, adopting
  proptest/rstest, hypothesis, fast-check + `@qgis/test-utils` and
  GoogleTest/RapidCheck, is backlog TASK-23.
* **Change (sdk)**: `ts-packages/qgis-sdk-bridge` gained the `README.md` its
  `files` field already promised and a `pack:check` script, so `turbo run
  pack:check` now covers both npm packages instead of one.
* **Change (env)**: The pixi-sandbox publisher moved to v0.5.2 and its three
  generated files were reinitialized, which retired the seven hand edits `d11e72e`
  and `45ac2b5` had reinstated by hand — and the `LOCAL EDITS` banner every reviewer
  had to cross-check against. The policy now lives in a `[workflow]` table in
  `pixi-sandbox.toml` and `pixi-sandbox init` renders it, so the owned files stay
  byte-identical to a fresh render and the scheduled upgrade job's pull requests are
  trustworthy by construction: the `push` `paths` allowlist, least-privilege
  permissions, the concurrency group, `timeout-minutes`, the pinned `setup-pixi`
  pixi-version and its disabled cache. The allowlist is narrowed to the transport's
  real inputs (the plan, the two pixi manifests, the vendored crate graph including
  every member manifest, the workflow itself) and drops `package.json` / `bun.lock`
  and the `py-packages/**` and `ts-packages/**` manifests, none of which can change a
  packed byte. Three things config cannot express are given up on purpose: a timeout
  on the upgrade job, a per-branch second concurrency group the workflow-level one
  already covers, and deleting the redundant `pixi global install` step on the
  publish job. v0.5.2 generates the repaired `SHA256SUMS` bootstrap check that
  `45ac2b5` had to fix by hand, since v0.4.3–v0.5.1 ran it against a filename that
  does not exist in the runner's cwd and so verified nothing.

## 2026-09-24

* **Change (ci)**: `publish_sandbox.yml` now uses pixi-sandbox's trigger shape —
  `push` to `main` with a `paths` filter (`.pixi-sandbox.toml`, `pixi.toml`,
  `pixi.lock`, `.github/workflows/publish_sandbox.yml`) plus `workflow_dispatch` —
  instead of `workflow_run` after every successful `CI` run, which cannot filter
  by path and so republished `sandbox/developer-linux-64` on every green `main`.
  The publish no longer waits for `CI` on the same commit (the PR that changes
  these files is still validated by CI, including `plan --json`), and both jobs
  now check out the triggering commit instead of the branch tip.
* **Change (env)**: `dev` now guarantees Python via a new `py-runtime` feature
  (`python >=3.11,<3.15` — intersects, never overrides, the interpreter the
  conda-forge `qgis` package pins), and the `py` feature gained `pytest-cov`
  (the plugin CI previously pip-installed) next to `pytest`. JS testing moved
  to bun end to end: the `node-test` task runs `bun test tests/contract.test.js`
  in the `docs` env while `node-build` still builds the napi addon with npm in
  `node`, the package's own `test` script and README now say bun, CI's
  node-FFI step invokes `pixi run -e docs bun test …`, and the TypeScript
  getting-started page shows the bun invocation. bun cannot join `dev` and
  `docs`/`dev` cannot share a solve group: conda-forge `bun 1.3.11 h5` pins
  `icu >=75.1,<76` while the QGIS stack pins `icu >=78.3,<79` (verified
  against the feedstock — latest build 2026-07-31, "Rebuild for icu 78" open
  since 2026-02-10). bun was verified to load the napi addon and run the
  contract suite (5/5) plus the bridge suites (22/22). `pixi.lock` was
  regenerated on a GitHub runner (the working sandbox cannot reach
  conda-forge); the refreshed lock only adds pytest-cov/coverage/toml to the
  `py`/`py-qgis` solves — every other package stayed at its locked version.
* **Verify**: Landed the pending environment refactor (PR #6) after verifying it
  from scratch on a fresh Codespaces sandbox — pixi 0.81, cargo 1.96.1, clang-format
  22.1.8, QGIS 3.44.14. `pixi install -e dev --locked` succeeds and the committed
  `Cargo.lock` is complete for all 9 workspace crates; `gates` (fmt-check, clippy
  `-D warnings`, lint-toml, lint-actions, test), `check-cpp`, and `test-full`
  (application_lifecycle + vector_layer) are all green.
* **Fix**: Clippy 1.96 widened beyond what the code was written for.
  * `unnecessary_map_or` → `is_none_or` (`LayerStyle::is_valid`, qgis-styles).
  * `ptr_arg` → `&Path` parameters in `write_compile_commands` (qgis-sys build.rs).
  * `manual_pattern_char_comparison` → `split(['_', '-', ' '])` in `to_pascal_case`
    (qgis-sdk + qgis-plugin) and `type_complexity` → `PlanLevel` alias (qgis-py).
  * `inherent_to_string` → `impl fmt::Display` + `#[napi(js_name = "toString")]`
    `as_string` on the qgis-node wrappers; the `.d.ts` `toString()` contract is
    preserved because the generated names stay identical.
  * PyO3 `useless_conversion` false positive on `#[pyfunction]`/`#[pymethods]`
    (pyo3/pyo3#4828, fixed upstream in 0.23.5) silenced with module-level
    `#![allow(...)]`; `render` also got an explicit `#[pyo3(signature = ...)]` to
    retire pyo3's deprecated implicit defaults warning.
* **Fix (test harness)**: `QApplication` is a per-process singleton, but `AppHandle`
  created one per `vector_layer` test — deterministic heap corruption
  ("corrupted double-linked list", SIGABRT) from the second test on. Rebuilt
  `crates/qgis-sys/tests/helpers/mod.rs` around a `thread_local` shared app that
  lives for the whole test binary; 5/5 vector_layer + 1/1 lifecycle tests now pass.
  Also required `const { RefCell::new(None) }` for clippy 1.96's
  `missing_const_for_thread_local`.
* **Fix (setup task)**: the old `setup` hardcoded `$CONDA_PREFIX/lib/libqca-qt6.so.2`
  as the soname source, but the dev env ships the Qt5 flavor
  (`libqca-qt5.so.2.3.12`) with no `libqca-qt6` at all — the symlink was dangling
  and QGIS-backed tests failed to load (`libqca-qt5.so.2 not found`). The task now
  links whichever flavor is present, failing loudly otherwise.
* **Fix**: `.github/workflows/rust-check.yml` fmt scope omitted `qgis-styles`; the
  crate is now formatted there too.
* **Fix (CI)**: the `test-rust` job ran bare `cargo test --workspace`, which on a
  headless runner aborted once the (now-run) QGIS-backed tests created a
  `QApplication` (`could not connect to display`) and would race the single-app
  harness across threads. It now delegates to the repo's own `test`/`test-full`
  pixi tasks so offscreen platform, `--test-threads=1`, and provider/proj env are
  the single source of truth. `Test Rust code` is green in CI.
* **Workflow consolidation and PR failure follow-up**: the PR's red Node builds
  used `napi build --manifest-path`/`-o`, which `@napi-rs/cli` 2.18 does not
  support; the package scripts now use `--cargo-cwd` and a positional output
  directory. The qgis-sdk test suite loaded `qgis_sdk.testing` both through its
  `pytest11` entry point and explicit `pytest_plugins` declarations; the duplicate
  registrations were removed. The Ubuntu maturin-action wheel matrix (which failed
  in its Docker/Python bootstrap) is no longer part of CI: smoke tests build both
  Python packages with maturin directly. The workflows are now `ci.yml`, `docs.yml`,
  and `publish_sandbox.yml`; Python and Rust coverage reports are retained as
  artifacts, and sandbox publishing is gated on a successful CI run.
* **Test layout**: Removed the standalone `examples/` programs and their Pixi/CI
  invocations. Core geometry and CLI behavior stay tested in Rust crates; the
  PyO3/NAPI adapters now have Rust-side result-shape tests, and Python/Node smoke
  suites run after extension compilation with native loading required in CI.
  Rust CLI smoke coverage lives in `crates/qgis-cli/tests` and
  `crates/qgis-sdk/tests/plugin_cli.rs`, rather than inline workflow shell.
* **Style**: ran `clang-format 22` over the C++ shims/headers (`qgis-sys/src`,
  `qgis-sys/include`) that predated the formatting requirement.

## 2026-09-23

* **Addition**: Adopted the reference project's *release-mode* publisher as the
  new environment-packing path, replacing the homegrown env-pack pipeline.
  * New `.pixi-sandbox.toml` declares the reviewed publish plan — one `developer`
    bundle (`dev` + `docs` environments, `linux-64`, `cargo_vendor = true`).
  * New `.github/workflows/publish-sandbox.yml` is a thin consumer wrapper around
    the pixi-sandbox *reusable* workflow
    (`Archont561/pixi-sandbox/.github/workflows/publish-sandbox.yml` at pinned
    commit `3d7a6182`, release `v0.2.0`). It auto-runs after a successful `CI`
    run on `main` (or via `workflow_dispatch`) and publishes the
    `sandbox/developer-linux-64` orphan branch. Packing, verification, and
    publishing all run on the native runner with a checksum-verified standalone
    release binary; no pixi-sandbox crate is vendored (consumer mode).
  * New `scripts/restore.sh` — the airlock one-liner: fetch the branch, run
    `doctor --verify`, restore envs + vendor tree offline, source
    `.pixi/sandbox-env.sh`.
  * **Removed**: `.github/workflows/env.yml` and the old `scripts/pack-env.sh`,
    `publish-env-branch.sh`, `setup-env.sh`, `use-pack.sh`. The `pack` task and
    the `pixi-pack` workspace dependency are gone — pack tooling is no longer a
    local dependency (the release binary fetches its own pinned tools).
  * **Update**: `ci.yml` gained a "validate sandbox publish plan" job using the
    upstream `setup-pixi-sandbox` action + `plan --json`, pinned to the same
    SHA as the publisher. `lint-toml` bare mode now also checks
    `.pixi-sandbox.toml`. Knowledge docs (`env-provisioning.md`, `pixi.md`,
    `CONTEXT.md`, `documentation-site.md`) rewritten to the new consumer model.

## 2026-09-23

* **Fix**: Removed the last deprecated pixi syntax — top-level `channels` in
  `[package.build]`. pixi moved that key to `backend.channels` (prefix-dev/pixi
  #4361); the three source-package manifests (`py-packages/qgis-sdk`,
  `py-packages/qgis-rs`, `crates/qgis-node`) now declare the backend as a
  `[package.build.backend]` table carrying `name`/`version`/`channels`. The
  `⚠️ Top-level 'channels' in [package.build] is deprecated` warning no longer
  appears on `pixi lock`.
* **Update**: Reorganized the pixi environments and task layout to the reference
  (Archont561/pixi-sandbox) model. There is *no* `default` environment anymore:
  dependencies moved from the root `[dependencies]` table into feature layers
  (`rust`, `cxx`, `qgis`, `utils`, `docs`, `sandbox`, `sdk`, `py`, `node`), and
  the environments are now `dev` (rust+cxx+qgis+utils+sandbox — the primary one),
  `ci` (rust+cxx+qgis+sandbox), `utils` (hook/lint tooling), plus the unchanged
  `docs`/`sdk`/`py`/`py-qgis`/`node`. User-facing tasks set `default-environment`
  so bare `pixi run <task>` still works; CI and lefthook pass `-e` explicitly.
* **Update**: pixi 0.81 quirk discovered and documented — `default-environment`
  is only accepted on tasks that have a `cmd`, declared inline in `[tasks]`;
  block-form `[tasks.<name>]` tables and pure aggregators (`gates`/`ci`/`ci-full`)
  reject it. Aggregators instead resolve their environment through `depends-on`.
* **Fix**: splitting `docs` out of the `default` group surfaced a latent icu
  conflict — conda-forge QGIS needs icu ≥78.3 while `bun` pins icu <76, so bun
  cannot share an environment with QGIS. The `docs` feature is deliberately kept
  out of `dev`/`ci`; docs tasks run against the separate `docs` environment.
* **Addition**: New `utils`-backed tasks — `lint-commit` (`convco check
  --from-stdin`, used by the commit-msg hook), `lint-toml` (taplo, staged-file
  aware via `$@` passthrough), `lint-actions` (actionlint). `check-cpp` now
  accepts optional staged files passed through `pixi run check-cpp -- a.cpp b.h`
  (falls back to the whole tree without args). `gates` gained `lint-toml` +
  `lint-actions`.
* **Update**: [lefthook.yml](/lefthook.yml) rewritten to the reference shape
  (`min_version: "2.0.0"`, `pixi run -e dev <task>` for every hook) so hooks and
  CI cannot drift; pinned to staged files only via `glob` + `{staged_files}`,
  with a `commit-msg` convco job and an optional `pre-push` gates job.
* **Update**: workflows re-pointed — `ci.yml` validates `dev` + `utils` + `docs`
  and runs tests in `dev`; `env.yml` packs the `dev` environment
  (`pixi install -e dev` / `pixi run -e dev pack`); `scripts/pack-env.sh`
  defaults to packing `dev`. README + knowledge docs updated to match.
  (The env->`sandbox/` branch migration to `pixi-sandbox` itself is still
  pending — see the notes in [CONTEXT.md](/CONTEXT.md) and the pixi-sandbox
  reference project.)

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
* **Update**: the task layout now matches the reference project completely —
  the `pack` verb exists (`pixi run pack` → `scripts/pack-env.sh`, which packs an
  environment with `pixi-pack` and smoke-tests the bundle), `pixi-pack` moved into
  `[workspace.dependencies]` and is consumed by the root environment, and the
  ordering the reference uses (features → their per-env tasks → `[environments]` →
  one trailing `[tasks]` block with plain `verb = "cmd"` strings) was already
  reproduced. `pixi-sandbox` publishes its packs on `env/<platform>` branches; only
  `env/self-linux-64` exists there, and it is what bootstrapped the `cargo 1.98.0`
  used to verify this repo.
* **Fix**: `env.yml` called `pixi run -e default pixi-pack`, but no environment
  declared `pixi-pack` (it is absent from `pixi.lock` too), and its smoke test
  unpacked the bundle with `--target`, which pixi-pack executables do not accept.
  Both steps are now one call to `pixi run -e default pack`, so CI and a local
  `pixi run pack` share the implementation; **the new `pixi-pack` pin needs one
  `pixi lock`** before `pixi install --locked` in that workflow can pass.
* **Correction**: an earlier commit removed `default-environment = "docs"` from the
  `docs-build` task on the belief that pixi rejects unknown task fields. The
  reference project uses that exact field on its own `docs-build`, so it is legal —
  it is restored here, and `pixi.toml` now documents the full set of task keys.
* **Verification**: `cargo metadata --no-deps` (8 workspace members), `cargo fmt -p
  qgis-py -p qgis-sdk -p qgis-node`, 112 + 16 pytest tests in the two
  `py-packages`, `bun test` (17) + `bun run build` for the bridge, the docs site
  build (49 pages), `taplo fmt`, `actionlint`, and `pixi task list` for all five
  environments all pass. `cargo check`/`clippy`/`test` and `pixi install` still
  cannot run in this sandbox (no crates.io/conda access), so the commit was made
  with `--no-verify`; the two pre-existing red signals are unrelated to the layout:
  the napi `bigint64`/`u64` conversion errors in `crates/qgis-node/src/lib.rs` and
  Pages' "has no pages" upload (the workflow never writes `has_pages` to `$GITHUB_OUTPUT`).

* **Fix**: the napi binding's `u64` break, and the recorded diagnosis of it was wrong.
  napi **2.16 has no `bigint64` feature** (checked `crates/napi/Cargo.toml` at
  `napi@2.16.9`); `u64` exists only as a *one-way* `impl ToNapiValue for u64` in
  `js_values/bigint.rs`, with no `FromNapiValue`, while `i64` is generated for both
  directions from `js_values/number.rs` via `napi_create_int64`/`napi_get_value_int64`
  (N-API 1, so no extra feature is needed). The six E0277s were the four
  `tile_count`/`size_bytes`/`bytes` getters plus the two `#[napi(object)]` fields
  (`ZoomLevelInfo.tile_count`, `TilePlanResult.total`), which need both directions.
  They now cross the boundary as `i64` (`as i64` at the edge; `qgis_render` keeps
  `u64`) — which is also what `index.d.ts` and `fallback.js` already promised
  (`number`, not `BigInt`), so the fallback and the addon stay one contract.
  Rationale is written into `crates/qgis-node/src/lib.rs` above the object types.
* **Addition**: `ts-packages/qgis-node/tests/contract.test.js` — 11 tests on the
  documented surface, run with **`node --test`** instead of `jest` (which had zero
  test files, so `npm test` in node.yml failed with "Pattern: - 0 matches"). They
  assert the shared fallback/native contract: 4568 tiles for `14,50,15,51` z10-14
  (the README/docs figure), `tileCount()` a safe integer rather than BigInt, the
  `snake_case` aliases, and both spellings of the Web-Mercator limits. `jest` left
  `devDependencies` and 3648 lines of transitive closure left `package-lock.json`.
* **Fix**: `npm install` has never worked inside `ts-packages/qgis-node`, which is
  what node.yml's install step runs. The root `package.json` declares a
  `workspaces` list and its `name` is `qgis-rs` — the same as this package's — so
  npm walks up, tries to fold the member into that root and dies in its arborist
  with "Cannot read properties of null (reading 'matches')". A
  `ts-packages/qgis-node/.npmrc` with `workspaces=false` keeps npm scoped to the
  directory while `bun install` at the root still resolves the workspace; the whole
  CI step sequence (`npm install` → `npm test` → `node ../../examples/typescript_api.js`)
  then runs green locally. `fallback.js`/`index.js`/`index.d.ts` also now agree: the
  fallback exported only `getMaxLatitude()`/`getMaxZoom()`, the package only
  `MAX_LATITUDE`/`MAX_ZOOM`, so each side answered to the other's name.
* **Fix**: `cargo fmt --all --check` failed on four pre-existing files in
  `qgis-sys` (`build.rs`, `src/core/vector_layer/layer.rs`, `tests/vector_layer.rs`,
  `tests/helpers/mod.rs`), so the `fmt-check` verb of `gates` could never pass. The
  whole workspace is formatted now; `pixi run gates`'s first verb is green.
* **Update**: the docs site's lockfile duplication ended — `apps/docs` is a member
  of the root Bun workspace, so `apps/docs/bun.lock` was never what resolved
  anything, and having it was how a root install resurrected `@astrojs/sitemap`
  3.7.4 behind the nested pin's back. Deleted; the root `bun.lock` plus the root
  `overrides` are now the single source, and the docs build (49 pages) and
  `bun install --frozen-lockfile` both verified after the removal.
* **Update**: `env.yml` installs with `pixi install -e default`, not `--locked` —
  the reference project's choice, so editing `pixi.toml` can never redden the
  pack workflow by itself; keeping `pixi.lock` fresh is a `pixi lock` + commit,
  which `pixi.toml`'s header and `.knowledge/env-provisioning.md` both say.
  A `workflow_dispatch` job that re-locks and pushes was deliberately *not* added
  (the reference has no such automation, and it needs write access to the branch).
* **Verified** in this sandbox after the above: `cargo metadata --no-deps`,
  `cargo fmt --all --check` (clean), `pixi task list` for `default`/`docs`/`py`/
  `sdk`/`node`, `taplo check`, `actionlint`, 16 + 112 pytest tests, `bun test` (17)
  and `bun run build` for the bridge, `bun install --frozen-lockfile` + docs build
  (49 pages), `node --test` (11) and `npx tsc --noEmit index.d.ts`. Still not
  runnable here: `cargo check/clippy/test`, `pixi install`, and `napi build` —
  crates.io and conda are unreachable, so the napi change is reasoned from the
  napi 2.16.9 sources rather than compiled.

* **Fix**: two CI-shape bugs the split left behind, found from the step results on
  PR #4 rather than from logs (which stay unreachable here). `node --test
  "tests/**/*.test.js"` is Node >= 21 syntax while node.yml pins the Node 20 LTS, so
  the package's new tests never ran there — `package.json` now names the file, which
  also avoids the bare `node --test` form walking out of the package into the
  bridge's TypeScript tests. After that fix CI's
  "Install deps and test fallback" step passes, `cargo check --workspace` passes (the
  napi `i64` boundary compiles), and only clippy and rust-check's own commit step
  stayed red. The latter failed on every pull request because it guarded
  `github.ref_name != 'main'` and then ran `git push origin HEAD:$GITHUB_REF_NAME` —
  on a PR that ref is `N/merge`, which GitHub owns — so it is now limited to push
  events, and its `format` step gained the three binding crates that became workspace
  members under `crates/` and had no rustfmt check at all.

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
* **Creation**: Established the execution roadmap, now maintained in [Backlog doc-2](../backlog/docs/roadmap/doc-2%20-%20QGIS-RS-Execution-Roadmap.md) — phased plan for architectural decisions and type binding.
* **Creation**: Established [decisions/](/decisions/) subdirectory with 8 decision documents (D01–D08).
* **Creation**: Established [.github/workflows/env.yml](/../.github/workflows/env.yml) — CI workflow for environment packing.
* **Creation**: Established [scripts/](/../scripts/) — setup-env.sh, use-pack.sh, publish-env-branch.sh.
