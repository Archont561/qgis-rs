---
id: TASK-50
title: Add C++ coverage measurement for the native manager
status: To Do
assignee: []
created_date: '2026-10-07 12:08'
updated_date: '2026-10-07 12:08'
labels:
  - testing
  - coverage
  - cpp
  - tooling
dependencies: []
references:
  - crates/xtask/src/cpp.rs
  - .github/workflows/ci.yml
documentation:
  - .knowledge/build-system.md
priority: medium
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The coverage lane measures Rust (cargo-llvm-cov lcov), Python (pytest-cov XML per package) and JavaScript (bun --coverage), and uploads those to Codecov. Nothing measures the C++ in `crates/qgis-sys`, so a C++ regression can only show up as a failing assertion, never as a coverage delta, and TASK-49 AC#1 asks Codecov for a separate native component that does not exist yet.

What is unmeasured today:

- `conversions.cpp` (80 lines) — the QGIS-free half of the manager, exercised by the 14-case GoogleTest/RapidCheck suite in `crates/qgis-sys/tests/cpp`, which `pixi run test-cpp` builds through cmake + ninja into `target/cpp-tests` and runs under ctest.
- `manager.cpp` (925 lines) — the owner thread, registry, dispatch and every handler; it runs only inside the Rust `qgis`-feature tests, and the cc build that links it into those test binaries carries no instrumentation.
- `crates/qgis-sys/include/native_manager/generated/*` — generated fragments, which need an explicit policy instead of a silent gap.

Constrained by the offline environment: the `clang`/`clang++` drivers are absent (LLVM 22.1.8 ships clang-check, clang-query, clang-tidy and clang-format only), so LLVM-instrumented C++ coverage is not available here; the GCC toolchain (14.4.0) does provide `gcov` with `--json-format`, while `gcovr` and `lcov` are absent and conda-forge is unreachable from the sandbox. Either the report is rendered by a converter this repository owns (D10: an xtask subcommand), or a new tool is added through a runner-side pixi.lock change like TASK-24's.

This task only adds measurement. Raising the numbers, and the repository-wide 95 percent target, stay with TASK-49.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A single offline command (for example `pixi run xtask cpp-coverage`) instruments the C++ translation units, runs the suites that execute them, and writes a report under `target/coverage/` beside the Rust, Python and JavaScript artifacts. No new pixi dependency and no network access are required for it to run.
- [ ] #2 `conversions.cpp` coverage is enforced rather than printed: the command fails when coverage drops below the recorded threshold, and the measured numbers and the exact command that produced them are recorded in this task's notes.
- [ ] #3 `manager.cpp` is measured from the Rust `qgis`-feature tests, the only place it executes, by instrumenting the cc build and merging the profiles from those runs; anything left uncovered is either a test gap or an explicit reviewed exclusion with a reason, never an omission.
- [ ] #4 The report is uploaded to Codecov as its own native component, while `pixi run test-cpp`, `pixi run gates` and the default gate keep their current behaviour and cost: coverage stays a separate stage exactly as the Rust and Python coverage producers are today.
- [ ] #5 A note in `.knowledge/` or the docs records what is instrumented, with which compiler and flags, why the LLVM route is unavailable in this environment, how the profiles are collected and merged, and how a developer reproduces the report offline.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Run the coverage command offline and record the measured totals, the command line and the report paths in the implementation notes.
- [ ] #2 Run `pixi run test-cpp` and `pixi run gates` and confirm both still pass with the coverage build absent from the default gate.
- [ ] #3 Confirm the native component appears in the Codecov report for the merged commit, or record in the notes why that verification belongs to the runner rather than the sandbox.
<!-- DOD:END -->
