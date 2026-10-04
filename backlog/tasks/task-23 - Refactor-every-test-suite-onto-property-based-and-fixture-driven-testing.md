---
id: TASK-23
title: Refactor every test suite onto property-based and fixture-driven testing
status: In Progress
assignee: []
created_date: '2026-10-02 23:06'
updated_date: '2026-10-04 10:54'
labels:
  - refactor
  - testing
milestone: m-4
dependencies: []
documentation:
  - .knowledge/testing.md
  - .knowledge/decisions/D11-tests-outside-src.md
  - >-
    backlog/docs/refactor/doc-3 -
    Repository-Refactor-and-Test-Modernization-Plan.md
  - >-
    backlog/docs/testing/doc-5 -
    QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Now that src/ and tests/ are split in every crate and package (D11), the suites are tables of hand-picked examples: one extent, one zoom range, one project file. The invariants they are really about — an extent round-trips through its text form, a tile plan's per-level counts sum to its total, every operation answers with the envelope the protocol declares — are statements about *all* inputs, and should be tested as such.

Adopt one property library and one fixture library per language, in the layout the split just created:

| Language | Fixtures / structure | Properties |
| --- | --- | --- |
| Rust | `rstest` | `proptest` |
| Python | `pytest` (already there) | `hypothesis` |
| TypeScript | `@qgis/test-utils` (already in-repo) | `fast-check` (already a bridge dev-dependency) |
| C++ | GoogleTest | RapidCheck |

The C++ shim (`crates/qgis-sys/src/**.cpp`) has no tests of its own today — it is reached only through the cxx bridge from Rust — so that row is new work rather than a migration: a test target wired into the `@qgis/rust` package scripts and the gate, running headless with `QT_QPA_PLATFORM=offscreen`.

Do this suite by suite, and keep the example-based tests that document a specific known answer (the 4568-tile pyramid, `tile_from_lon_lat(10, 13.9, 51.1)`): a property and a golden value answer different questions, and the golden values are what pin the three language clients to each other.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Rust: proptest and rstest are workspace dependencies, and qgis-render (extent, tiles, crs) plus qgis-protocol have property tests for their round-trips and invariants
- [ ] #2 Rust: repeated setup uses rstest fixtures and cases instead of a hand-rolled helper fn per test file
- [x] #3 Python: hypothesis is a test dependency of both distributions, with strategies for extents, zoom ranges and CRS auth ids
- [ ] #4 TypeScript: the client suites use @qgis/test-utils for shared setup and fast-check for the same invariants the Rust properties assert
- [x] #5 C++: a GoogleTest target builds and runs the shim's own tests headless, with RapidCheck properties for the string and handle conversions
- [x] #6 The C++ suite is wired into turbo so that pixi run ci covers it
- [x] #7 The cross-language golden values survive the migration and still agree
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Repository-wide assessment and sequencing plan: backlog/docs/refactor/doc-3 - Repository-Refactor-and-Test-Modernization-Plan.md

The plan is intentionally documentation-only; implementation must proceed in small behavior-preserving slices after the Pixi environment is restored.

2026-10-03: Started the first executable P0 slice. Added proptest coverage for extent round trips/intersection symmetry, zoom-range invariants, tile-level counts, CRS normalization, and protocol request/response envelopes. Added rstest fixture usage for shared tile bounds, Hypothesis dependencies plus pure Python property coverage for both distributions, and a fast-check extent round-trip property at the Node boundary.

2026-10-03: The Python fake-source property exposed that `feature_count=0` was replaced by the default ten features; the fake now preserves an explicit zero. Existing shared layer golden fixtures remain in place for Rust, Python, and TypeScript.

2026-10-03: TASK-23 remains In Progress. Cargo, Pixi, QGIS, and Bun are unavailable in this checkout, so the focused Rust/Python/TypeScript gates and C++ GoogleTest/RapidCheck target still need execution and implementation in the restored environment. The backlog CLI was also unavailable, so this status/note update is the documented manual fallback.

Testing utilities and bridge-contract execution is decomposed into TASK-31 through TASK-35.

TASK-31 defines the shared bridge contract; TASK-32 covers Python fixtures; TASK-33 covers the TypeScript harness; TASK-34 covers shared vectors; TASK-35 covers Qt/QGIS/WebEngine gates.

2026-10-04: AC#5 and AC#6 are done, measured on a restored sandbox. The edge conversions of the shim - the JSON envelope, the handle encoding, and the C ABI malloc/free pair - moved out of manager.cpp into crates/qgis-sys/src/native_manager/conversions.cpp, which has no QGIS behind it and can therefore be loaded without starting QGIS. crates/qgis-sys/tests/cpp builds that one translation unit against GoogleTest 1.18 and RapidCheck under the same warnings-as-errors contract build.rs uses, and runs 14 tests headless: 9 examples and 5 properties covering envelope round-trip, failure detail merge, handle round-trip over the exact-integer range, fractional-handle rejection, and a byte-exact NUL-terminated response copy. xtask test-cpp drives cmake, ninja and ctest; the @qgis/rust test script calls it, so pixi run ci covers the suite. cmake and ninja from TASK-24, and gtest and rapidcheck, were already declared in pixi.toml and present in the offline pack, so this needed no new dependency and no pixi lock.


2026-10-04: two findings from the property run. First, a property over arbitrary byte strings failed because QString::fromStdString replaces invalid UTF-8 with U+FFFD, collapsing distinct inputs onto one key; the properties now generate printable ASCII and the replacement behaviour is pinned by example instead of hidden. Second, clang-tidy reads compile_commands.json, which the qgis-sys build script writes only for the sources cargo compiles, so the CMake-built suite is excluded from clang-tidy while cpp_sources now includes it for clang-format - before this, C++ test files were invisible to the format-drift gate.

2026-10-04: AC#2 and AC#4 are NOT met and the task stays In Progress. AC#2: rstest is a workspace dependency but is used in exactly one file (crates/qgis-render/tests/tiles.rs); every other crate still hand-rolls its per-file setup helper. AC#4: ts-packages/qgis-node uses fast-check and ts-packages/qgis-sdk-bridge uses @qgis/test-utils, but the bridge suite has no fast-check property, so the two client suites do not yet assert the same invariants the Rust properties do.
<!-- SECTION:NOTES:END -->
