---
id: TASK-55
title: Refactor C++ conversions tests into BDD-style GoogleTest scenarios
status: Done
assignee: []
created_date: '2026-10-09 10:06'
updated_date: '2026-10-09 10:16'
labels:
  - testing
  - cpp
dependencies: []
priority: medium
type: chore
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Refactor crates/qgis-sys/tests/cpp/conversions_test.cpp into behavior-oriented GoogleTest suites with explicit Given/When/Then sections, preserving every example and RapidCheck property and the native coverage baseline (conversions 33/34 lines, 76/160 branches). No new test dependency. Also covers a red-then-green fix for the handle ceiling, which the header documents as 2^53 but the code does not enforce.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 AGENTS.md carries the C++ behavior-test style rule
- [x] #2 conversions_test.cpp uses behavior-oriented suite and test names with Given/When/Then sections
- [x] #3 All 16 original cases preserved (11 examples, 5 properties), each mapped to its new name
- [x] #4 Handle ceiling: a failing test for whole numbers above 2^53 is added first, then the fix makes it pass
- [x] #5 Native coverage matches baseline: conversions 33/34 lines, 76/160 branches, manager 451/566
- [x] #6 pixi run test-cpp, pixi run xtask cpp-coverage, format checks and pixi run gates pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commits: docs b-rule 2a4489b; test envelope 17ba447 handle, response renames; ce76e1b red 2^53 test; 1a3a117 fix. Gates not yet run at task notes time.

Baseline before: 16 cases (11 examples, 5 properties), conversions 33/34 lines 76/160 branches, manager 451/566. After: 18 cases (12 examples, 6 properties). All 16 originals present (ResponseBuffer and FailureNamesAKindAndCarriesItsMessage renamed) with equal assertion counts; two ASSERT_FALSE(fixture.isEmpty()) added.

Coverage after the fix (cpp-coverage exit 0): conversions 32/33 lines (97.0%), 74/158 branches; manager 451/566 and 85/96 functions unchanged; total 500/616 lines, 110/121 functions, 911/2178 branches. The uncovered line is still the allocation-failure return. The drop is the removed covered comparison number > UINT64_MAX, which the 2^53 check replaces, so the denominators shrink by one line and two branch outcomes. No executed line lost coverage. AC5 numbers are restated for this reason.

Corrected commit list: docs 2a4489b; envelope 17ba447; handle 844dee2; response 58f52aa; red 2^53 test ce76e1b; fix 1a3a117; evidence f3840cb.

pixi run gates exit 0 on f3840cb: Rust 328 + 30 runs (358), doctests 6, qgis-sdk 405+3 skipped plus 3 and 5 qt/qgis gates, qgis-rs pytest 21 (434 total), Bun 37+99+13 = 149, C++ ctest conversions passes with 18 cases.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Refactored crates/qgis-sys/tests/cpp/conversions_test.cpp into Envelope, Handle and ResponseBuffer behavior suites with Given/When/Then sections and ASSERT prerequisites, with no new dependency. Every original assertion is kept (two prerequisite ASSERTs added). The 2^53 handle ceiling was pinned red, then fixed in conversions.cpp. C++ now has 18 cases (12 examples, 6 RapidCheck properties), up from 16. Coverage: conversions 32/33 lines, the lost line being a covered comparison made redundant by the fix. The uncovered allocation-failure line is unchanged. Gates green. Not pushed.
<!-- SECTION:FINAL_SUMMARY:END -->
