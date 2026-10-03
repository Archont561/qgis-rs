---
id: TASK-23
title: Refactor every test suite onto property-based and fixture-driven testing
status: To Do
assignee: []
created_date: '2026-10-02 23:06'
updated_date: '2026-10-03 08:43'
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
- [ ] #1 Rust: proptest and rstest are workspace dependencies, and qgis-render (extent, tiles, crs) plus qgis-protocol have property tests for their round-trips and invariants
- [ ] #2 Rust: repeated setup uses rstest fixtures and cases instead of a hand-rolled helper fn per test file
- [ ] #3 Python: hypothesis is a test dependency of both distributions, with strategies for extents, zoom ranges and CRS auth ids
- [ ] #4 TypeScript: the client suites use @qgis/test-utils for shared setup and fast-check for the same invariants the Rust properties assert
- [ ] #5 C++: a GoogleTest target builds and runs the shim's own tests headless, with RapidCheck properties for the string and handle conversions
- [ ] #6 The C++ suite is wired into turbo so that pixi run ci covers it
- [ ] #7 The cross-language golden values survive the migration and still agree
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Repository-wide assessment and sequencing plan: backlog/docs/refactor/doc-3 - Repository-Refactor-and-Test-Modernization-Plan.md

The plan is intentionally documentation-only; implementation must proceed in small behavior-preserving slices after the Pixi environment is restored.
<!-- SECTION:NOTES:END -->
