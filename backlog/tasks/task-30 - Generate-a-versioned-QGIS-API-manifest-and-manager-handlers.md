---
id: TASK-30
title: Generate a versioned QGIS API manifest and manager handlers
status: In Progress
assignee: []
created_date: '2026-10-03 08:57'
updated_date: '2026-10-07 20:23'
labels:
  - rfc
  - ffi
  - cpp
  - codegen
  - api
milestone: m-0
dependencies:
  - TASK-25.4
documentation:
  - >-
    backlog/docs/architecture/doc-4 -
    QGIS-Native-Manager-and-API-Coverage-Strategy.md
  - .knowledge/decisions/D12-qgis-native-manager-over-c-abi.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build the version-pinned extraction and generation pipeline described in the QGIS Native Manager and API Coverage Strategy. Read QGIS public headers together with binding/ownership metadata, normalize declarations into an explicit support manifest, and generate manager operation registrations, codecs, protocol metadata, documentation, and coverage reports. Start with core/data modules; keep GUI, private, provider-specific, and unsupported declarations explicit rather than silently dropping them.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The generator records every discovered public declaration as supported, supported_manual, partial, unsupported, host_only, provider_optional, or deprecated with a reason and QGIS version range.
- [x] #2 The generated manifest produces compilable manager handlers/codecs and an api.describe capability report without introducing a second hand-written operation spelling table.
- [x] #3 Ownership, invalidation, overload, enum, QVariant, binary-artifact, and paging mappings are explicit and have representative runtime tests.
- [x] #4 Rust, Python, TypeScript, and C++ consume shared protocol fixtures for generated core operations and exact error envelopes.
- [x] #5 A QGIS upgrade produces an API diff and fails review when declarations are silently dropped or ownership metadata changes.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03: Started the first vertical slice with a version-pinned core/data manifest at `crates/qgis-sys/native_manager/generated/api_manifest.json`. It records explicit declaration statuses, QGIS version ranges, ownership, operation/handler mappings, exclusions, and representative mapping policies.

2026-10-03: Added `pixi run xtask api-manifest [--check] [--diff-against PATH]` implementation. It validates manifest status/reason/version invariants, rejects dropped declarations/operations and ownership changes during upgrades, and deterministically generates the native-manager operation table and manifest-version header.

2026-10-03: Native `engine_info` now advertises manifest metadata, and `api_describe` routes through the generated handler registry. Cross-language/runtime gates and the full clang-AST extraction/API-diff pipeline remain outstanding; keep this task In Progress until Pixi/QGIS validation is available.

2026-10-03: Added required per-operation codec metadata to the manifest and generated registry, and exposed it through `api_describe.operation_metadata`; Python and TypeScript contract tests now advertise the capability as well. The manifest/registry still require compile-time validation once Cargo/QGIS tooling is available.
2026-10-06: Made the manifest the single authority for wire spellings. `qgis-protocol`'s `Operation::all()` and the manifest's `operations` were two hand-maintained lists of the same snake_case names with nothing comparing them — the second spelling table AC#2 forbids. A sixth repo lint, `pixi run xtask check-api-operations`, now requires the manifest to *partition* the 29 served names: 17 generated operations plus 12 named by explicit exclusions (`engine-transport`, `engine-geometry-and-tiles`, `engine-project-inspection`), each with a status and a reason. `Exclusion` gained an optional `operations` field (manifest_version stays 1); `validate_manifest` rejects an operation that is both generated and excluded, excluded twice, or excluded under a `supported*` status. Proven by damage, not by a green print: dropping `layer_fields`, renaming `layer_open`, and adding a protocol-only `layer_rename` each exit 1 naming the drift (the rename names both directions). Seven new tests in `crates/xtask/tests/api_manifest.rs` (13 total).

AC status after this slice — none ticked, all still have unproven parts: AC#1 covers only the reviewed core/data slice, with no clang-AST extractor (worth recording: the `default` env has no `clang++` driver, but `clang-check`/`clang-query` plus `qgis-sys`'s `compile_commands.json` make `clang-check -ast-dump=json` a viable offline extractor); AC#2's compile half is proven here (the generated `operation_table.inc` is `#include`d by `manager.cpp` and the 22-test `qgis`-feature suite is green) and its no-second-table half is now enforced, but the codec side is still one `json_object` for every operation; AC#3 still lacks representative runtime tests per mapping category; AC#4 has no shared fixtures for generated operations; AC#5 has `check_upgrade` and its test but no pinned baseline manifest in the gate.

2026-10-07: Added seven QGIS-feature runtime tests at the public native_manager_ffi::invoke JSON boundary in crates/qgis-sys/tests/api_mappings.rs. They cover distinct manager-owned IDs, invalidation after close, request-bearing getFeatures filtering, stable enum names, integer/string QVariant scalars, path-based PNG/GeoJSON artifact metadata, and gap-free offset/limit paging. Verified with pixi run -- cargo test --offline -p qgis-sys --features qgis -- --test-threads=1: 18 passed, including the seven new mapping tests. AC#3 is proven; TASK-30 remains In Progress while the other criteria are open.

2026-10-07 (correction): two records from the earlier slices were superseded by measurement this session. (1) The 2026-10-03 claim that `clang-check -ast-dump=json` is a viable offline extractor path is wrong: clang-check rejects the value in its own option parser (`for the --ast-dump option: json is invalid value for boolean argument`), and the pass-through form `-extra-arg=-Xclang -extra-arg=-ast-dump=json` exits 0 with zero bytes on stdout, a silent no-op. Verified alternatives, both needing `-isystem $CONDA_PREFIX/lib/gcc/*/include`: textual `clang-check -ast-dump` (45.6 MB for `conversions.cpp` alone) and `clang-query` with `set output detailed-ast` — `match cxxMethodDecl(ofClass(hasName("QgsVectorLayer")))` returned 292 matches, 271 from `qgis/qgsvectorlayer.h`, 14 from `QtCore/qcompilerdetection.h`, 4 from `QtCore/qobjectdefs.h` (Q_OBJECT trampolines), so the extractor must filter by expansion location before claiming to enumerate public declarations. The environment also ships zero `*qgis*.sip` files — the 861 `.sip` belong to PyQt5 — so AC#1 has no QGIS binding metadata input and its first slice is headers plus manual overrides. The reviewed id `QgsVectorLayer::QgsVectorLayer(uri,name,provider)` abbreviates the header signature by dropping `const QgsVectorLayer::LayerOptions&`; it is left as reviewed data for the extractor slice to regenerate. (2) The Rust test arithmetic in the 2026-10-06 note and the session log was wrong: in the gate the workspace nextest pass (295) already contains every test of the `qgis-sys/qgis,qgis-mcp/qgis` pass (29) — verified by set-comparing the two test listings, intersection equal to the second pass — so distinct Rust tests are 295 (288 before this slice added seven) plus 5 doctests, and the carried-forward "310 = 288 + 22" double-counted all 22.

2026-10-07 (AC#5): The gate had an API diff it never ran. `check_upgrade` could already refuse a dropped declaration or changed ownership, but `RepoLint::CheckApiManifest` called `run(true, None)`, so the diff path had no trigger outside unit tests. A pinned reviewed snapshot now sits beside the manifest at `crates/qgis-sys/native_manager/generated/api_manifest.baseline.json` (QGIS 3.44.14, 17 declarations, 17 operations), and one `verify_repository(root)` — used by the gate lint and by `api-manifest --check`, so the documented command cannot print a green a lint would fail — diffs it before checking the generated fragments. New `check_baseline(pinned, current)` is exact in both directions (declaration or operation added, dropped, re-owned, restatused; changed handler, codec or requires_initialization; moved manifest version or QGIS version pin) and reports every drift in one run; a filled-in promotion command rides in the failure text, and `scaffold` prints it too. doc-4 verification gate 8 now names the mechanism. Proven by damage on the real tree: dropping `QgsVectorLayer::fields` with its operation exits 1 naming both; re-owning `Qgis::version` exits 1 printing `Some("borrowed_snapshot") -> Some("qgis_owned")`; a pin that gained an unreviewed declaration exits 1 naming it — each restored and re-verified green. `crates/xtask/tests/api_manifest.rs` grew 13 to 19 tests, including one that builds a scratch tree, passes it, then damages it three ways and requires the same `verify_repository` to name the drift each time. Residual: no real QGIS upgrade was exercised — one QGIS (3.44.14) exists in this environment and the package indexes are unreachable — so the AC is proven at file level through the gate entry point rather than by moving the QGIS minor. pixi run gates green at 301 workspace tests; AC#5 ticked.

2026-10-07 (AC#2): Added per-operation `request_codec` and `result_codec` identifiers to the version-1 API manifest, generated C++ operation table, compiled manager registry, and `api.describe.operation_metadata`; retained `codec: json_object` as the generic envelope for compatibility. The generator validates identifier syntax, the pinned baseline reports request/result codec drift, and scaffold output gives new operations placeholder values. The public `qgis_sys::native_manager_ffi::invoke` test requires non-placeholder codec identifiers for all 17 operations and distinct `render_map`/`layer_open` profiles. Verified with `pixi run xtask api-manifest --check`, `pixi run xtask check-api-operations`, xtask manifest/scaffold tests, and the full QGIS-feature qgis-sys test suite. This supersedes the 2026-10-06 status sentence above that said the codec side remained one `json_object`; AC#2 is now proven, while AC#1 and AC#4 remain open.

2026-10-07: Expanded test-fixtures/layer-lifecycle.json to carry complete versioned success and invalid_object_id response envelopes. Rust protocol and native-manager integration tests, Python and Node client tests, and the C++ conversion suite now read the same cases. The live manager test compares layer_open, layer_info, layer_features, layer_close, and exact invalid-ID envelopes, substituting only the fixture path and runtime layer ID. Focused Rust, Python, Bun, C++, and QGIS-feature tests passed.
<!-- SECTION:NOTES:END -->
