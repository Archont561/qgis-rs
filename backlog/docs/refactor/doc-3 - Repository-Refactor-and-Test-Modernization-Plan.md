---
id: doc-3
title: Repository Refactor and Test Modernization Plan
type: guide
created_date: '2026-10-03 08:42'
---

# Repository refactor and test-modernization plan

## Purpose and guardrails

This is an assessment and sequencing plan, not an implementation. It covers the complete repository source/test surface in Rust, Python, TypeScript/JavaScript, and the C++ shim boundary. The goal is to make the code easier to change and the tests better at finding regressions while preserving the current public behavior, protocol shapes, generated examples, and cross-language golden values.

The refactor skill's rules apply to every work item:

1. Establish or strengthen a test before changing structure.
2. Make one cohesive extraction or simplification at a time; keep commits reversible.
3. Keep public imports, CLI flags, serialized JSON, generated file names, error text where it is part of the contract, and QGIS lifecycle behavior stable unless a separate compatibility decision is approved.
4. Prefer a small function, data type, fixture, or adapter over a framework or abstraction invented only to satisfy DRY/SOLID.
5. Keep example/golden tests for interoperability values. Property tests supplement them; they do not replace the known 4,568-tile pyramid, known tile coordinates, protocol examples, or generated bridge snapshots.
6. Do not make PyQGIS a dependency of the CLI path. Reuse Rust for pure parsing, planning, serialization, and validation where that is already the repository's direction.

### Principles applied pragmatically

- **DRY:** remove duplicated *stable policy* (wire decoding, scaffold writing, runtime selection, fixture construction), not every repeated assertion or example. A test should remain readable at the point of use.
- **KISS:** keep orchestration linear and push complexity into named pure components. Avoid a universal repository-wide fixture or transport abstraction until at least two consumers have the same contract.
- **SOLID:** split mixed responsibilities, define narrow interfaces at runtime/QGIS/network/filesystem/process seams, and inject those seams only where they improve deterministic testing. Fakes must obey the same observable contract as their real adapter.
- **Behavior first:** use characterization tests and golden vectors to describe current behavior before moving code. A large file is a prioritization signal, not proof that it needs a rewrite.

## Inventory and evidence

The static scan covered `src` and `tests` below. The current shell cannot run `cargo` or restore Pixi, so the inventory and plan are static; execution gates are listed later and no test result is implied here.

| Area | Current surface | Evidence / implication |
| --- | --- | --- |
| Rust | 76 `.rs` source/test files, about 9,280 lines, 30 test files, 127 `#[test]`/`#[tokio::test]` attributes | `rstest`, `proptest`, QuickCheck, and similar crates are declared or available in places but are not used by the scanned Rust tests. Most tests are examples and hand-built cases. |
| Python | 54 source/test files, about 16,647 lines, 162 `test_` functions | `qgis-sdk` has useful pytest fixtures and fakes in `tests/conftest.py`/`qgis_sdk.testing`; `qgis-rs` has almost no shared fixture layer. Hypothesis is available in the Pixi Python environment but is not used. |
| TypeScript/JavaScript | 25 source/test files, about 3,625 lines, 49 test calls | `@qgis/test-utils` already contains the shared fixture boundary and one `fast-check` suite. Bridge facade modules repeat transport/decode/fallback logic. |
| C++ shim | `crates/qgis-sys/src/core/application/{app,info}.cpp` and `core/vector_layer/layer.cpp`, about 155 lines | The shim is exercised indirectly from Rust/QGIS tests, but there is no direct C++ test target for handle, string, null, exception, or lifecycle behavior. |

### Complete surface disposition

This is the coverage map for the plan. “Preserve” means the area is included in test/contract work even when no production extraction is initially justified.

- **`qgis-render`:** `crs.rs`, `extent.rs`, `tiles.rs`, `project.rs`, `render.rs`, and their five test modules. Highest-value pure-domain property target.
- **`qgis-protocol`:** `lib.rs` and `tests/protocol.rs`. Keep serde/golden compatibility; add generated arbitrary values only where the protocol permits them.
- **`qgis-engine`:** `lib.rs`, `payload.rs`, and `tests/engine.rs`. Split dispatch/envelope/operation concerns after envelope characterization tests.
- **`qgis-cli`:** `cli.rs`, `commands.rs`, `lib.rs`, `main.rs`, and CLI/command/MCP/parsing tests. Separate argument parsing and pure command planning from filesystem/process/QGIS execution.
- **`qgis-mcp`, `qgis-server`, `qgis-node`, and `qgis-py`:** retain their adapter/routing contract tests; reduce duplicated forwarding and error mapping only after shared protocol vectors exist.
- **`qgis-styles`:** all style/color/labeling/layout/renderer/symbol modules and four test modules. Start with fixture builders and serde/property invariants, not a broad style-model rewrite.
- **`qgis-sdk` and `xtask`:** library, CLI, scaffold, CI, lint, release, and utility code plus their integration tests. Make binaries thin and keep command planning pure.
- **`qgis-sys`:** Rust wrappers, three QGIS integration suites, `tests/helpers/mod.rs`, and the three C++ files. Keep QGIS/Qt tests serialized and add a native shim gate.
- **Python `qgis_sdk`:** all listed modules, with priority on `scaffold.py`, `testing.py`, `tasks.py`, `network.py`, bridge codegen/description/runtime/window, and CLI/UI integration tests.
- **Python `qgis-rs`:** `tests/test_api.py` and `tests/test_cli.py`; add reusable project/CLI fixtures and cross-language vectors without adding PyQGIS calls to CLI tests.
- **TypeScript/JavaScript:** `qgis-sdk-bridge` transport/window/facades/framework adapters, `qgis-node` contract adapter, and `@qgis/test-utils` fixture/bridge-global modules. Keep all package tests in the verification matrix.

## Prioritized work packages

Priority is based on user impact, regression risk, and leverage for subsequent work. P0/P1 work establishes safety and removes the most consequential duplication; P2 work improves cohesion after the contracts are stable; P3 work is opportunistic cleanup.

### P0 — executable safety and test migration anchor

**P0.1 Establish characterization and golden-vector gates (TASK-23 anchor).**

Before production extraction, record the current results for:

- Rust protocol and engine envelopes, including success/error variants and unknown-operation behavior.
- Render extent/CRS/tile/zoom examples, including the known 4,568-tile pyramid and known tile coordinates.
- Python scaffold output trees and key generated contents for no-UI, UI, web, React, Vue, Web Components, and Rust variants.
- Python bridge descriptions and generated `.d.ts` output.
- TypeScript bridge callback/Promise behavior, fallback behavior, and node adapter contract.
- C++/Rust wrapper null/error/lifecycle behavior when QGIS is available.

Store cross-language wire fixtures in a small, versioned fixture area (prefer a shared `tests/fixtures/protocol` location only for data that is genuinely language-neutral). Do not put Python-only fake objects or generated whole projects into that directory. Rust, Python, and TypeScript should each consume the same JSON vectors for protocol/description contracts. Keep large QGIS data such as `points.gpkg` in the existing fixture location.

**P0.2 Move every test suite toward fixture-driven and property-based testing.**

Use TASK-23 as the migration checklist, with these boundaries:

- Rust: use `rstest` for readable matrices and `proptest` for algebraic/serialization invariants. Put small domain strategies next to the domain tests first; create a shared support crate only if the same wire fixture is consumed by multiple Rust crates.
- Python: add Hypothesis to the test environment/package test instructions and create strategies for pure SDK inputs. Use pytest fixtures for runtime, filesystem, fake transport, QGIS application, and generated-project setup. Do not generate arbitrary live PyQGIS objects.
- TypeScript: extend `@qgis/test-utils` with factories and `fast-check` arbitraries. Keep generated fixtures isolated per test and keep golden bridge examples as explicit examples.
- C++: add a direct GoogleTest target, then use RapidCheck only for pure shim conversions where it produces useful coverage. Do not property-test global QGIS state or Qt event-loop lifecycle.

Fixture scopes must be explicit: pure/unit fixtures must not initialize QGIS; QGIS fixtures must be session/function scoped as required by Qt and serialized; generated-project fixtures must use a temporary directory and return both the path and a manifest of expected files; network/task fixtures must expose recorded calls and deterministic outcomes.

**Exit gate:** all existing tests still run, golden vectors are checked in, at least one representative property suite exists in each language where a pure invariant exists, and integration tests are marked/isolatable from QGIS-free tests. This is migration work, not permission to delete examples.

### P1 — Rust core and boundary cohesion

#### P1.1 Pure geometry and protocol domain (`qgis-render`, `qgis-protocol`)

Targets: `crates/qgis-render/src/{crs,extent,tiles,project,render}.rs`, their tests, and `crates/qgis-protocol/src/lib.rs`.

- Add explicit domain constructors/validation only where current behavior is implicit; retain existing public types and serialization.
- Add properties for extent parse/serialize round trips, validity and intersection laws, CRS normalization/auth-id behavior, zoom-range normalization, tile coordinate/bounds relationships, tile-count sums, and image/render option normalization.
- Add protocol properties for serde round trips, operation/error-kind closure, required/optional field behavior, and engine envelope invariants. Keep hand-written known vectors for interoperability and error messages.
- Deduplicate repeated `Extent`/`ZoomRange` setup through small `rstest` fixtures/builders, not a generic GIS fixture framework.
- If `project.rs` mixes path validation, QGIS execution, and render planning, extract only a QGIS-free request/plan type first; leave QGIS behavior behind the existing adapter.

**Verification:** `cargo test -p qgis-render -p qgis-protocol`, property cases with bounded finite values, and cross-language protocol vectors. Test invalid/non-finite inputs explicitly; avoid unbounded generators that make shrinking opaque.

#### P1.2 Engine dispatch and CLI planning

Targets: `crates/qgis-engine/src/lib.rs`, `payload.rs`, `tests/engine.rs`, `crates/qgis-cli/src/{cli,commands,lib,main}.rs`, and `crates/qgis-mcp/src/lib.rs`.

- In `qgis-engine`, characterize the existing `send`/`ok`/`err` behavior, then extract typed envelope decoding, operation dispatch, and individual handlers. Make the top-level function a thin dispatcher. Reuse `qgis-protocol` types rather than re-creating JSON maps.
- Replace repeated engine test payload construction with named request fixtures and table-driven cases; retain assertions that prove exact wire envelopes.
- In `qgis-cli`, separate clap parsing, pure command planning, filesystem/process execution, and QGIS-backed execution. Keep CLI exit codes, stdout/stderr, and JSON output unchanged.
- In `qgis-mcp`, isolate tool registration/schema from handlers and shared error conversion. The tool contract should be tested against the same protocol/golden fixtures as CLI and engine.
- In `qgis-server`, keep routing behavior and add route-table/property tests for normalization, method matching, and error mapping before considering any router abstraction.
- In `qgis-node` and `qgis-py`, keep adapters thin and add contract tests for the same engine request/response values; do not make either adapter a second engine.

**Verification:** parser/command tests without QGIS, engine/MCP contract vectors, CLI subprocess tests for output compatibility, and QGIS integration tests only for the execution seam.

#### P1.3 SDK CLI/scaffold and workflow tooling

Targets: `crates/qgis-sdk/src/lib.rs`, `crates/qgis-sdk/src/bin/qgis-plugin.rs`, and `crates/xtask/src/{ci,lints,release,scaffold,util}.rs`.

- Make `qgis-plugin.rs` a thin argument-to-library adapter. Extract cohesive modules for command parsing, scaffold request normalization, template/render selection, filesystem writes, and validation. Do not maintain two independent scaffold implementations without a documented contract.
- Compare Rust SDK templates with Python `qgis_sdk/scaffold.py` templates. First add generated-file manifest/golden tests and identify intentional language-specific templates versus accidental source-of-truth duplication. Only then centralize metadata or shared contract fragments.
- For `xtask`, separate pure plans (files/commands/targets) from process execution and environment discovery. Inject a narrow command runner/filesystem seam in tests; do not mock every standard-library call. Keep CI/lint/release commands and failure text compatible.

**Verification:** matrix tests for all scaffold options, generated manifest and selected-file snapshots, dry-run command plans, and an actual subprocess smoke test after environment restoration.

### P1 — Python SDK decomposition and fixture migration

#### P1.4 Scaffold pipeline

Target: `py-packages/qgis-sdk/src/qgis_sdk/scaffold.py` (about 2,118 lines; `scaffold_plugin` about 682 lines), plus `cli.py`, UI tests, bridge tests, and scaffold-related Rust templates.

Extract in this order, preserving the current `scaffold_plugin` public entry point:

1. A validated immutable scaffold options/model object (plugin name, destination, UI/web/framework/Rust choices).
2. A template catalog/rendering layer, with templates grouped by contract (base plugin, UI, web framework, bridge, Rust).
3. A filesystem writer that creates directories/files and returns a manifest; it must reject path escapes and report collisions consistently with current behavior.
4. A small orchestration function that selects templates, invokes the writer, and runs optional validation.
5. CLI argument translation as a separate adapter.

Use fixture-driven tests for each option combination, generated manifest tests, and snapshots only for stable generated files. Hypothesis can generate valid/invalid plugin identifiers, destinations, optional feature combinations, and metadata values; explicit examples must cover every supported framework and known generated bridge contract. Do not snapshot every generated file if a manifest plus representative contract files gives the same safety.

#### P1.5 Testing fakes and pytest plugin surface

Target: `py-packages/qgis-sdk/src/qgis_sdk/testing.py` (about 1,675 lines), `tests/conftest.py`, and `tests/test_testing.py`.

Split fake families into narrow modules or clearly separated sections: interface/actions, dialogs/webviews, bridge, network, tasks, processing/features, and shared call recording. Keep `qgis_sdk.testing` as a compatibility export/pytest-plugin facade so existing plugin tests do not change imports. Use protocols for the behavior consumed by production code and dataclass state for deterministic fakes.

The fixture contract should provide resettable call logs, configurable outcomes, and factories instead of mutable module-level defaults. Add contract tests proving each fake's observable behavior against the corresponding production adapter's protocol. Keep the real `qt_app`/QGIS fixture separate from pure fake tests.

#### P1.6 Network and tasks

Targets: `network.py` (about 1,199 lines), `tasks.py` (about 1,448 lines), `bridge/qgis_api/network.py`, `bridge/qgis_api/tasks.py`, and their tests.

- **Network:** separate QGIS network-manager transport, requests-like response normalization, retry/backoff policy, session/decorator configuration, and content fetching. Inject a narrow transport protocol. Test status/code/header/body normalization, retry boundaries, redirect behavior, and history with Hypothesis-generated bounded responses plus explicit QGIS-manager examples.
- **Tasks:** separate task state/result value objects, task execution/manager adapter, decorator/signature wrapper, and chain/group composition. Preserve Celery-like public methods (`delay`, `apply_async`, `s`, `si`, result state) and cancellation semantics. Use state-machine or transition properties only for the pure fake/task model; use examples for exception and callback ordering.
- Apply the same adapter boundary to `bridge/qgis_api/*` rather than adding another independent implementation.

#### P1.7 Bridge descriptions/code generation and UI/runtime adapters

Targets: `bridge/{codegen,description,decorators,loader,runtime,window}.py`, `bridge/qgis_api/*.py`, `ui.py`, `qt.py`, `runtime.py`, `processing_bridge.py`, and corresponding tests.

- Treat the bridge description as a contract model: validate names/types, deterministic ordering, JSON serialization, and Python-to-TypeScript generation. Share golden description vectors with TypeScript.
- Separate environment discovery, bridge loading, description generation, and runtime invocation. Keep QGIS/Qt discovery behind the existing optional runtime boundary.
- In `ui.py`, isolate declarative specification, Qt construction, web-dialog loading, and event/callback plumbing. Test pure specifications with fakes and keep Qt event-loop tests marked/integration-scoped.
- Review `plugin/{base,decorators,registry}.py`, `algorithm.py`, `metadata.py`, `styles.py`, and `bootstrap.py` for duplicated registration/metadata normalization. Prefer a small shared normalizer only when the same fields and error semantics are proven identical.

**Python verification:** `pytest` pure suite, Hypothesis runs with deterministic profiles and bounded examples, generated-project fixtures, and a serialized QGIS/Qt integration group with `QT_QPA_PLATFORM=offscreen`. `py-packages/qgis-rs` CLI tests must continue to work without PyQGIS.

### P1 — TypeScript/JavaScript bridge cohesion

#### P1.8 One typed call/transport adapter

Targets: `ts-packages/qgis-sdk-bridge/src/qgis/{iface,layers,message,network,processing,project,settings,tasks}.ts`, `qgis.ts`, `description.ts`, `loader.ts`, and `window.ts`.

The facades repeat raw callback invocation, JSON decoding, bridge fallback, and mock fallback. Add characterization tests first, then introduce one narrow typed call/transport adapter that owns:

- callback-versus-Promise normalization;
- JSON response decoding and error conversion;
- bridge-present/bridge-absent selection;
- recorded/mock transport injection for tests.

Feature modules should retain their public methods and only define API-specific names/types. Do not hide all APIs behind an untyped dynamic index signature. Add compile-time and runtime tests for unknown methods, malformed responses, thrown callbacks, and fallback selection.

#### P1.9 Split `window.ts` responsibilities and framework wrappers

`window.ts` (about 361 lines) currently combines environment discovery, channel connection, dynamic proxy creation, event dispatch, and connection state. Extract internal modules/interfaces in that order, keeping `window` exports stable. Model connection state explicitly so reconnect/dispose/event behavior can be tested without a browser.

Review `react.ts`, `vue.ts`, `svelte.ts`, and `webcomponents.ts` for a shared lifecycle pattern. Extract only the common subscribe/dispose behavior after two or more wrappers have identical semantics; framework-specific hooks remain in their own modules.

#### P1.10 Shared TypeScript test utilities and node contract

Targets: `ts-packages/test-utils/src/{bridge-globals,fixture,index}.ts`, its tests, and `ts-packages/qgis-node/{src,index.js,tests/contract.test.js}`.

Extend `@qgis/test-utils` with resettable bridge fixtures, typed API-description factories, callback/Promise arbitraries, and temporary fixture restoration. Use `fast-check` for method names/arguments, response decoding, fixture restoration, and description/proxy consistency; retain explicit vectors for known bridge APIs. The node adapter should consume the same contract vectors and test its error/serialization boundary, not reimplement browser behavior.

**TypeScript verification:** typecheck, Biome, package tests, fast-check suites with bounded shrinking, and cross-package contract tests under Bun.

### P2 — styles and remaining adapters

After P1 contracts are stable:

- `qgis-styles`: add reusable readable builders for colors, symbols, renderers, and layouts; property-test serde round trips, valid range invariants, and stable default/omission behavior. Keep style fixtures local to style tests and do not create a universal GIS fixture.
- `qgis-server`: use parameterized route cases and properties for path/method normalization; keep integration tests for actual server startup.
- `qgis-cli`/`qgis-mcp`/`qgis-node`/`qgis-py`: remove only duplication proven by shared protocol contracts; preserve separate adapter error messages where clients rely on them.
- `plugin`, `algorithm`, `metadata`, and processing bridge: consolidate registration/metadata code only after characterization tests show identical field precedence and failure behavior.

### P1/P2 — C++ shim boundary

Targets: `crates/qgis-sys/src/core/application/{app,info}.cpp` and `core/vector_layer/layer.cpp`, their Rust wrappers, and `crates/qgis-sys/tests/{application_info,application_lifecycle,vector_layer}.rs`.

Add a minimal native test target under the existing qgis-sys build conventions using the Pixi `gtest` and `rapidcheck` dependencies already declared in `pixi.toml`. Keep it small and headless:

- GoogleTest examples for UTF-8/empty strings, null handles, ownership/lifetime, exception-to-error translation, and application/vector-layer lifecycle.
- RapidCheck properties only for pure conversion/normalization helpers: repeated string conversion, valid handle round trips, and error preservation. Do not generate arbitrary `QgsApplication` graphs or run concurrent Qt state.
- A Rust integration test remains the source of truth for the public `qgis-sys` wrapper. The native target verifies the seam before Rust/QGIS integration makes failures harder to localize.
- Wire the target into the qgis-sys package/CI gate, with `QT_QPA_PLATFORM=offscreen` and serialized execution. If QGIS libraries cannot be linked in a lightweight native target, split pure shim helpers into a link-light target and keep a small QGIS-backed smoke target.

The C++ work is a boundary safety addition, not permission to redesign the generated CXX interface.

## Property and fixture catalog

The following properties are candidates; each must be implemented only when the input domain is valid and the shrinker produces useful cases.

### Rust

- `Extent`: parse then serialize then parse preserves normalized coordinates; valid extents have ordered finite bounds; intersection is commutative/idempotent where defined; containment agrees with bounds.
- `CRS`: normalized auth IDs round-trip and reject malformed forms consistently.
- `ZoomRange` and tiles: normalization is idempotent; every generated tile lies in the expected zoom/bounds; tile counts sum across zoom ranges; known pyramid totals remain explicit golden tests.
- Protocol/engine: valid requests serialize/deserialize; response envelopes contain exactly one success/error branch; operation and error enums remain closed; payloads preserve optional-field semantics.
- Styles: color/range and serde invariants after the P2 phase.

### Python

- Scaffold options: valid names render a manifest; invalid identifiers are rejected without writes; enabling a feature adds exactly its contract files; rendering is deterministic for the same options.
- Bridge descriptions: valid names/types serialize and generate deterministic TypeScript; decode/encode round trip preserves ordering rules.
- Network: response truthiness/status/body consistency; retry policy stops at configured boundaries; chunk concatenation preserves content.
- Tasks: legal state transitions preserve result methods; group/chain aggregation is associative only where the public contract says it is; cancellation is idempotent.
- Metadata/UI specs: normalization is deterministic and does not mutate caller-owned input.

### TypeScript/JavaScript

- Transport: callback and Promise paths normalize to the same result/error; JSON decode rejects malformed responses predictably; fallback selection is stable.
- Fixture lifecycle: create/reset/dispose restores globals and call logs; repeated setup/teardown is idempotent.
- Description/proxy: every supported description entry maps to one callable typed facade and unsupported entries fail consistently.

### C++

- Conversion helpers preserve empty/Unicode values and error status.
- Handle ownership and null behavior are deterministic; lifecycle cleanup is repeatable.

## Sequencing, dependencies, and ownership boundaries

1. **Restore environment and baseline:** resolve the recorded Pixi restore failure (TASK-24), then run the current gates. No refactor should be declared validated while Cargo/Pixi are unavailable.
2. **P0.1/P0.2:** add characterization vectors, test markers, fixture conventions, and one small property suite per pure language/domain. This is the TASK-23 migration anchor.
3. **P1 Rust pure domains:** render/protocol first, then engine/CLI/MCP. Their stable wire contracts unblock Python/TypeScript adapter work.
4. **P1 scaffold contracts:** characterize both Rust and Python scaffold outputs before extracting either implementation. Decide which pieces are intentionally language-specific.
5. **P1 Python internals:** fakes/fixtures first, then network/tasks, then scaffold/UI/bridge decomposition. Each extraction must leave `qgis_sdk` compatibility exports intact.
6. **P1 TypeScript transport/window:** add shared test-utils contracts, then extract transport, then feature facades, then framework wrappers.
7. **C++ boundary:** add native tests once the environment is restored; use failures to distinguish shim defects from Rust wrapper/QGIS defects.
8. **P2 styles and residual adapters:** only after the cross-language vectors and package gates pass.
9. **Final cleanup:** remove dead helpers and duplicate branches only after at least one full gate cycle proves no consumer remains.

Dependencies are deliberately directional: pure domain/protocol tests do not depend on QGIS; QGIS integration depends on restored Pixi/Qt; Python/TS bridge contract tests depend on shared description vectors; C++ native tests depend on the declared C++ test feature; full CI depends on all package-specific checks.

## Verification gates and rollback points

Every extraction has a local gate and a rollback point:

- **Before:** focused characterization/golden test is green, changed public symbols are listed, and the extraction has one responsibility.
- **During:** run the smallest affected package test plus formatter/linter/type checker; compare generated manifests and serialized fixtures.
- **After each package:** run the package's full unit/property tests and compatibility tests before moving to another language.
- **Integration:** run QGIS/Qt tests with `QGIS_PREFIX_PATH`, `QGIS_PLUGINPATH`, `QT_QPA_PLATFORM=offscreen`, and serialized execution; run C++ native tests; run Python and Rust adapter contracts.
- **Cross-language:** compare shared JSON/description vectors in Rust, Python, and TypeScript; retain golden output diffs as review artifacts.
- **Final:** run the repository's `pixi run gates` (or the documented fast equivalent), including formatting/linting, Rust tests/coverage gates, Python pytest, Bun tests/typechecks, scaffold/package checks, and C++ tests.

If a refactor changes a golden value, public export, generated file, CLI output, protocol field, or error classification, stop and treat it as a behavior change requiring a separate decision. Revert the structural step or restore the compatibility adapter rather than updating the fixture automatically.

## Definition of done for the plan

The plan is complete when TASK-23 links to this document, each source/test area above has an explicit disposition, the first implementation slices can be reviewed independently, and the resulting work preserves existing examples while adding useful properties and deterministic fixtures. This document does not claim that any refactor or test migration has been implemented.
