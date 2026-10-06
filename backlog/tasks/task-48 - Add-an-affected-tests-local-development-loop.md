---
id: TASK-48
title: Add an affected-tests local development loop
status: Done
assignee:
  - '@me'
created_date: '2026-10-06 18:48'
updated_date: '2026-10-06 18:59'
labels:
  - tooling
  - testing
  - performance
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add one tested xtask entry point that plans and runs only checks affected by working-tree changes while preserving reverse dependencies, shared-input fallbacks, Turbo caching, and the full pixi run gates pre-push authority.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 xtask affected compares tracked staged unstaged and untracked changes against a configurable Git base defaulting to the merge base with origin/main and reports a deterministic plan
- [x] #2 Rust changes select the owning crate and reverse-dependent crate tests; Python and TypeScript changes select affected workspace packages; documentation-only changes avoid native builds
- [x] #3 Global manifests lockfiles shared fixtures and build or gate automation conservatively select the full gate, with rename and deletion handled
- [x] #4 The planner has fixture-backed integration coverage for Rust Python TypeScript docs global-input rename deletion clean-tree and explicit-base cases
- [x] #5 Execution supports dry-run and force modes, keeps pixi run gates unchanged as the authoritative pre-push gate, and documents focused-loop usage and cache behavior
- [x] #6 Measured cold and warm representative edits show the affected loop avoids unrelated native work, and pixi run gates remains green
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Run focused xtask tests
- [x] #2 Run pixi run gates
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Add fixture-backed public planner tests first; implement Git change discovery and deterministic affected command plans; wire clap dry-run/force execution; document and measure focused versus full selection; run focused tests and gates.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-06: Public seam is xtask::affected::plan plus the affected CLI. Eighteen focused integration and CLI cases cover Rust, Python, TypeScript, docs, global inputs, clean trees, deletion, rename, untracked files, explicit bases, deterministic deduplication, and force parsing.

2026-10-06: Measured a formatted one-line test-utils edit with --base HEAD: only that package lint and 37 tests ran; cold 0.382s, warm 0.267s with both Turbo tasks replayed from cache. The full offline gate then passed in 3m00s, demonstrating that the inner loop avoided unrelated native builds while the authoritative gate remained unchanged.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added pixi run xtask affected: Git-aware discovery across branch, staged, unstaged, deleted, renamed, and untracked changes; reverse-dependent nextest selection for Rust; downstream cached Turbo selection for package work; conservative full-gate fallback for shared and unknown inputs; dry-run, base, and force controls; fixture-backed tests and testing documentation. Focused tests and the full gate pass.
<!-- SECTION:FINAL_SUMMARY:END -->
