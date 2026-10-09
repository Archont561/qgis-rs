---
id: TASK-50
title: Add C++ coverage measurement for the native manager
status: In Progress
assignee: []
created_date: '2026-10-07 12:08'
updated_date: '2026-10-09 08:24'
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

Constrained by the offline environment: the `clang`/`clang++` drivers are absent (LLVM 22.1.8 ships clang-check, clang-query, clang-tidy and clang-format only), so LLVM-instrumented C++ coverage is not available here; the GCC toolchain (14.4.0) does provide `gcov` with `--json-format`, while `gcovr` and `lcov` are absent and conda-forge is unreachable from the sandbox. Either the report is rendered by a converter this repository owns (D10: an xtask subcommand), or a new tool is added through a runner-side pixi.lock change like TASK-24's. Decision (2026-10-09): the tool route — `gcovr` is declared in `[feature.cpp-test.dependencies]`, and the lock is refreshed runner-side by the relock bot during the PR (the guard detects the drift, the bot commits the refreshed `pixi.lock`).

This task only adds measurement. Raising the numbers, and the repository-wide 95 percent target, stay with TASK-49.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A single offline command (for example `pixi run xtask cpp-coverage`) instruments the C++ translation units, runs the suites that execute them, and writes a report under `target/coverage/` beside the Rust, Python and JavaScript artifacts. The command runs in the default pixi environment with `gcovr` available (declared in `[feature.cpp-test.dependencies]`; the lock was refreshed runner-side by the relock bot) and requires no network access.
- [x] #2 `conversions.cpp` coverage is enforced rather than printed: the command fails when coverage drops below the recorded threshold, and the measured numbers and the exact command that produced them are recorded in this task's notes.
- [x] #3 `manager.cpp` is measured from the Rust `qgis`-feature tests, the only place it executes, by instrumenting the cc build and merging the profiles from those runs; anything left uncovered is either a test gap or an explicit reviewed exclusion with a reason, never an omission.
- [ ] #4 The report is uploaded to Codecov as its own native component, while `pixi run test-cpp`, `pixi run gates` and the default gate keep their current behaviour and cost: coverage stays a separate stage exactly as the Rust and Python coverage producers are today.
- [x] #5 A note in `.knowledge/` or the docs records what is instrumented, with which compiler and flags, why the LLVM route is unavailable in this environment, how the profiles are collected and merged, and how a developer reproduces the report offline.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Run the coverage command offline and record the measured totals, the command line and the report paths in the implementation notes.
- [x] #2 Run `pixi run test-cpp` and `pixi run gates` and confirm both still pass with the coverage build absent from the default gate.
- [x] #3 Confirm the native component appears in the Codecov report for the merged commit, or record in the notes why that verification belongs to the runner rather than the sandbox.
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: `gcovr >=8,<9` declared in `pixi.toml` `[feature.cpp-test.dependencies]` (next to gtest/rapidcheck, like TASK-24's cmake/ninja precedent). The sandbox cannot reach conda-forge, so `pixi.lock` is refreshed runner-side: the relock guard detects the drift on the PR and the pixi-sandbox bot commits the refreshed lock. The owned-converter route (a D10 xtask subcommand rendering gcov JSON directly) remains the fallback if the tool route is rejected in review.

2026-10-09: Claimed TASK-50. gcovr 8.3 is restored and available offline. Implement a separate xtask cpp-coverage stage with GCC instrumentation, real QGIS-feature test profiles, enforced conversions coverage, and native Codecov upload; preserve the default test and gates path.

2026-10-09: pixi run xtask cpp-coverage passed offline: conversions 33/34 lines, manager 451/566, generated operation table 17/17; total 501/617 lines, 110/121 functions, 913/2180 branches. Reports are target/coverage/native.xml, native.json, native-summary.json. Three public-seam tests pass including a deliberate below-95-percent failure. Focused cpp/ci tests and xtask Clippy pass; normal test-cpp remains green. Native Codecov upload is wired but runner visibility is not yet verified.

2026-10-09: Normal pixi run gates passed at 3644145: 356 Rust tests plus 6 doctests, 434 Python passed with 3 skipped, 149 Bun; normal ctest passed and no native coverage stage ran. Codecov visibility belongs to the runner: the coverage lane runs on main push or workflow_dispatch, and Codecov is outside sandbox network access. AC4 remains open pending actual native upload evidence.

2026-10-09: Final offline rerun with atomic GCC counter updates passed and reproduced every recorded total. Five coverage contract tests pass. The C++ suite currently contains 16 GoogleTest/RapidCheck cases (the initial task description says 14). Pinned Codecov action inputs were checked; uploads use explicit report files and disable search to keep native data in its own flag.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Native measurement is implemented with a separate offline xtask producer, GCC/gcov/gcovr, merged C++ and QGIS-feature profiles, a fail-closed 95 percent conversions floor, detailed reports, generated-code policy, and a native-flag Codecov upload. Local proof is green. Keep In Progress until AC4 upload evidence is available on the runner.
<!-- SECTION:FINAL_SUMMARY:END -->
