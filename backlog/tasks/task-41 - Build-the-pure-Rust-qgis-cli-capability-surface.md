---
id: TASK-41
title: Build the pure-Rust qgis-cli capability surface
status: In Progress
assignee: []
created_date: '2026-10-03 09:35'
updated_date: '2026-10-10 22:21'
labels:
  - cli
  - rust
  - testing
  - enhancement
milestone: m-3
dependencies:
  - TASK-40
documentation:
  - >-
    backlog/docs/architecture/doc-7 -
    Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md
  - crates/qgis-cli
  - crates/qgis-engine
  - crates/qgis-render
  - .agents/skills/refactor/SKILL.md
  - .agents/skills/tdd/SKILL.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the standalone GIS CLI contract from doc-7 without adding a PyQGIS/PyQt dependency to the pure path. Start with version, capabilities, doctor, validation, project manifest inspection, tile planning, batch planning, structured errors, deterministic artifacts, and explicit native-backend gates.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 version, capabilities, and doctor report engine, transport, backend, limits, and unavailable native capabilities
- [ ] #2 validate, inspect, tiles plan, and batch plan expose deterministic machine-readable behavior with stable exit codes
- [ ] #3 Pure CLI tests run without QGIS, Python, Node, or WebEngine and preserve existing qgis-cli behavior
- [ ] #4 Native-only render/export/serve paths fail explicitly when the backend is unavailable and never silently substitute semantics
- [ ] #5 Filesystem policy, atomic artifacts, JSON stdout, stderr diagnostics, cancellation, and resource limits have contract tests
- [ ] #6 Implementation follows red-green-refactor slices and preserves existing public command flags and golden values
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The qgis-cli binary this task builds is what TASK-58 ships through @archont561/qgis-node and qgis-py.

Approved discovery slice: version, capabilities and doctor; binary and engine discovery public seams. Pure doctor exits 0 with optional native backend explicitly unavailable. Preserve existing commands; remaining TASK-41 slices stay open.

Discovery slice implemented: version/capabilities/doctor share deterministic text/JSON reports; engine owns availability, protocol owns names, clap owns command names. Existing engine_info wire response, flags, and execution gates are unchanged. Pure doctor exits 0 for optional QGIS absence. Red tests observed for missing engine seam and each new command; focused pure suites pass, native discovery tests pass. cargo tree and ldd confirm the no-default-features binary has no QGIS/Qt/Python/Node/WebEngine dependency. AC2-AC6 remain open for later slices; full gate evidence follows.

Final discovery-slice evidence: pixi run gates exit 0 (8/8); CARGO_NET_OFFLINE=true pixi run -- bun x turbo run test --env-mode=loose exit 0 (12/12). Rust 327 + 30 (was 323 + 30); SDK 490 passed/3 skipped/8 deselected, qt 3, qgis 5, qgis-py-dist 18, Bun 160, CTest 1 target. Separate native-feature discovery run: CLI 3 and engine 2 passed. Pure focused suites: 58 integration tests plus 1 doc test; clippy -D warnings passed. No push/PR; AC2-AC6 remain open.

Approved validation slice implemented at the binary and checked-tile domain seams: validate extent/crs/zoom/tile, normalized deterministic JSON, syntax-only CRS, exits 0/10/2; legacy execution errors keep exit 1. Tile::checked_bounds guards invalid indices before arithmetic without changing existing bounds behavior. Each new kind and the domain guard had an observed red test before implementation. AC2 remains open because inspect/tiles plan/batch plan are not implemented; AC3-AC6 remain open for the overall task. Final gate evidence follows.

Validation slice verified: focused pure CLI/render suites 86 integration tests plus 1 doc test; native-feature validation subprocess suite 11/11; clippy -D warnings passed. pixi run gates exit 0 (8/8); offline loose-environment turbo test exit 0 (12/12), Rust 340 + 30 (was 327 + 30), SDK 490 passed/3 skipped/8 deselected, qt 3, qgis 5, qgis-py-dist 18, Bun 160, CTest 1 target. Existing 4568-tile golden values and legacy error behavior remain covered. No new external dependencies; no push or PR. AC1 remains the only checked criterion; remaining validation types and inspect/planning/artifact/resource/cancellation contracts are still pending.

Owner approved metadata-only inspect slice: qgis-cli inspect <project> [--json], file_metadata scope with qgis_validation not_performed, no XML/ZIP parsing. Public seams: CLI argv/streams/status, legacy info and discovery, observable filesystem side effects. Exits 0/2/10/11/14 are scoped to inspect; regular files and symlinks to regular files accepted. Red-green slices first; task remains In Progress with AC1 only checked. No push or merge authorized.

Metadata-only inspect implemented at the approved subprocess seams. Reports supplied path, extension-derived format and byte size with inspection=file_metadata and qgis_validation=not_performed. No contents/backend/network/artifact work. Symlinks follow regular targets; directories/special files, unsupported extensions and non-UTF-8 paths are invalid input. JSON failures carry code/message on stdout plus stderr diagnostics; exits 0/2/10/11/14 are scoped to inspect. Legacy info JSON/text and exit 1 are pinned; discovery still derives commands from clap, with no new engine operation or dependency.

Observed red-to-green for the missing command, missing-input classification, invalid/non-file classification, filesystem errors, human report and non-UTF-8 serialization panic. Pure CLI/render: 107 integration tests + 1 doc test passed. Native-feature CLI: 49 tests passed (20 inspection, 15 legacy CLI, 3 discovery, 11 validation). Pure clippy -D warnings, source/boundary checks, pure dependency tree and ldd checks passed. Docs build passed (50 pages). Full offline/loose turbo suite passed 12/12 (4 cached): Rust 361 + 30, SDK 490 passed/3 skipped/8 deselected, qt 3, qgis 5, qgis-py-dist 18, Bun 160, CTest 1 target. Repository gate result follows. AC1 remains the only checked criterion; this does not complete inspect manifests or AC2-AC6.

Repository gate passed after the focused local commit: pixi run gates exit 0, 8/8 (4 cached), with formatting, workspace Clippy and conventional-message hooks passing. Final help/docs clarify that inspect never initializes QGIS, but a native-enabled binary still needs its shared libraries; pure use is --no-default-features. No further runtime behavior change. Full task remains In Progress with AC1 only checked; no push or merge.

Owner approved a deterministic tile-planning slice plus a reconciliation of the
three surfaces that report a plan. `qgis-cli plan tiles --bounds ... --zoom ...`
counts an XYZ pyramid from an extent alone: no project argument, no file opened,
no backend initialised, nothing written. This is what the legacy
`tiles <project> --dry-run` cannot do, because that command shares the renderer
and so calls `Project::open` before counting anything.

The reconciliation is the substantive part. The engine said `tile_count`, MCP
said `total_tiles`, and MCP's per-level `tiles` was a *count* where the engine's
top-level `tiles` is the *enumerated array* — one word carrying two meanings
across a single boundary. All three now emit `qgis_render::TilePlanReport`,
defined once. The engine's wire response is byte-identical: Python reads
`planned["tile_count"]`/`planned["levels"]`, and Node reads `_planned.bounds`
and `_planned.zooms` as objects, so changing it would have broken two shipped
clients and quietly done TASK-42's work. MCP's output did change — `total_tiles`
to `tile_count`, `levels[].tiles` to `levels[].tile_count`, and the string
echoes of bounds/zoom became the structured values — and MCP was the only
in-repo consumer of the old names.

`plan` reuses the exit-10 category `validate` already established rather than
adding its own, so malformed input means the same thing whichever pure command
refused it. Exits are 0 success, 2 usage, 10 unreadable bounds/zoom or an
unordered extent/zoom range. Legacy `tiles` flags, its "Would render" wording
and the 4568-tile golden are now pinned byte-exact rather than by substring.

Public seams: new `crates/qgis-cli/tests/plan_tiles.rs` (15 tests) covers
argv/streams/status at the process boundary with `PATH=""` and an empty
tempdir — no-project success, golden per-level rows, the shared JSON key set,
determinism, no filesystem writes, exit codes, and JSON failures that keep
stdout parseable. Its `json_is_the_engine_and_mcp_answer` test asserts the CLI
report equals both the engine's `plan_tiles` result and the MCP tool's report,
which is what stops a fourth spelling appearing. `qgis-render` gained two tests
pinning the report's values and key names; `qgis-mcp` gained one pinning its
serialised keys; `crates/qgis-cli/tests/discovery.rs` now asserts `plan` is in
the parser-derived command list and adds no engine operation.

Observed red before green for the missing `plan` command, the missing
`TilePlanReport`/`report()` seam, the missing engine key names, and MCP's old
field names. Verification: pure focused suites passed; `cargo nextest
--workspace --no-default-features` **380 across 60 binaries** (was 361/59) and
native-feature **31 across 7** (was 30/7); 0 failures. Clippy `-D warnings`
passed for both profiles. `pixi run gates` exit 0, **8/8** (4 cached).
`CARGO_NET_OFFLINE=true pixi run -- bun x turbo run test --env-mode=loose
--force` exit 0, **12/12, 0 cached**: Python 490 passed/3 skipped/8 deselected,
qt 3, qgis 5, qgis-py-dist 18, Bun 160, CTest 1 target — all unchanged. No
lockfile drift: `Cargo.lock`, `pixi.lock` and `bun.lock` are untouched, the new
`qgis-mcp` dev-dependency being a workspace member already in the graph.
`ldd` on the `--no-default-features` binary shows only libc/libm/libpthread/
libgcc_s, and `cargo tree` confirms `qgis-mcp` stays out of the shipped binary.

TASK-41 stays In Progress with AC1 the only checked criterion. AC2 needs
`batch plan` as well as the now-shipped `validate`/`inspect`/`tiles plan`. XML
and container manifests still need parser dependencies locked and vendored on a
network-capable runner; native execution gates, atomic artifacts and filesystem
policy, cancellation and resource limits remain open. Nothing pushed or merged.

Approved reconstruction: qgis-cli plan batch --extents <csv> --zoom <range> [--json], alongside plan tiles and separate from unchanged legacy batch <project>. Reuse commands::parse_extent_rows and qgis_render::TilePlanReport. Report extent_count, summed tile_count and ordered extents with name/plan; no project, backend initialization or writes. Public seam is the real binary with isolated temporary HOME/config/cache and empty PATH, testing argv, streams, stable exits 0/2/10/11/14 and observable filesystem effects. No parser dependencies, cancellation or resource policy is introduced; AC2 stays open for full inspection scope.

Batch reconstruction implemented and verified: 20 subprocess cases under tests/plan_batch.rs, observed red then green for absent command, human report, domain/UTF-8 error classification, missing input and filesystem failures. Shared error categories reuse inspect Failure without changing legacy diagnostics or exits. JSON embeds the existing TilePlanReport and sums rows without tile enumeration or deduplication; CSV order, Unicode names, duplicate names, comments/header handling, empty work, finite coordinates, malformed-row line numbers and no partial output are pinned. Pure CLI/render/engine: 169 nextest tests across 21 binaries passed; native-enabled CLI: 106 across 11 passed. Pure clippy -D warnings, source/boundary checks passed; ldd shows only libc/libm/libpthread/libgcc_s, and normal dependency tree excludes MCP/Python/Node. Legacy batch and byte-exact tiles --dry-run golden pass. No serde dependency added. AC2 remains open for full project-manifest inspection and remaining task scope; full final fan-out/gate evidence follows.

Reconstruction-wide verification: pixi run gates exit 0, 8/8 (4 cached); forced offline/loose turbo tests exit 0, 12/12 with 0 cached: nextest 400/61 plus native 31/7, SDK Python 490 passed/3 skipped/8 deselected plus qt 3 and qgis 5, Python FFI 24, Bun 166, CTest 1. Final CSV characterization also pins empty names as labels (no output-name policy), within the existing 20 batch cases; all 20 pass on pure and native-enabled profiles. No production change was required for that legacy-parser edge. AC1 only remains checked; no push or merge.
<!-- SECTION:NOTES:END -->
