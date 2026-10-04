---
id: TASK-45
title: Remove the cxx bridge from the xtask scaffold template
status: Done
assignee: []
created_date: '2026-10-03 22:38'
updated_date: '2026-10-04 08:39'
labels:
  - tech-debt
dependencies: []
documentation:
  - .knowledge/decisions/D12-qgis-native-manager-over-c-abi.md
  - .agents/skills/tdd/SKILL.md
  - .agents/skills/refactor/SKILL.md
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`xtask scaffold` still generates a `cxx::bridge` module and a `#include "rust/cxx.h"` for every new binding crate, even though RFC 19 removed `cxx` and `cxx-build` from `crates/qgis-sys` entirely (see D12). Nothing is broken today, but the next crate scaffolded from the template would reintroduce the dependency four phases of work removed, and `xtask check-boundaries` would not catch it: that lint rules on edges between crates, not on what a generator writes. Either teach the template the native-manager shape D12 chose, or drop the C++ half of the template and let `scaffold` produce Rust-only crates.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The scaffold command no longer emits cxx::bridge, rust/cxx.h, or a per-concept C++/Rust source tree; it adds only a validated native-manager API-manifest operation and regenerated fragments
- [x] #2 Tests in crates/xtask/tests/scaffold.rs prove the manifest-only output and duplicate refusal, so the obsolete generator cannot return silently
- [x] #3 The manifest-only direction and rationale are recorded as the 2026-10-04 amendment to D12
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented test-first at the public xtask seam. Replaced the obsolete four-file CXX generator with an API-manifest operation scaffold, added manifest drift to the in-process CI repo lints, and retained setup-qca after a fresh restore proved the soname repair is still needed. Focused xtask tests increased from 37 to 42 across the same 8 integration-test binaries; check-boundaries and api-manifest --check pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
xtask scaffold now follows D12: it modifies only the reviewed native-manager API manifest and regenerates its two derived fragments. Help and automation documentation use the post-RFC-19 vocabulary, the gate checks generated fragments before compilation, and setup-qca reports an explicit no-op when the soname is already correct.
<!-- SECTION:FINAL_SUMMARY:END -->
