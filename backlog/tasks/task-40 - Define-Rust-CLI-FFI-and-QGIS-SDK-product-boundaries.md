---
id: TASK-40
title: 'Define Rust CLI, FFI, and QGIS SDK product boundaries'
status: Done
assignee: []
created_date: '2026-10-03 09:35'
updated_date: '2026-10-03 22:12'
labels:
  - architecture
  - cli
  - ffi
  - qgis-sdk
  - decision
milestone: m-3
dependencies: []
documentation:
  - >-
    backlog/docs/architecture/doc-7 -
    Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md
  - .knowledge/architecture.md
  - .knowledge/decisions/D09-wire-protocol-over-ffi.md
  - .knowledge/decisions/D12-qgis-native-manager-over-c-abi.md
priority: high
type: docs
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Turn doc-7 into the accepted implementation contract for qgis-cli, qgis-rs Python/Node clients, qgis-plugin/qgis-sdk tooling, and the QGIS-hosted qgis_sdk runtime. Keep shared protocol and Rust reuse explicit while separating command ownership, runtime ownership, and package dependencies.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The capability ownership matrix is reviewed and linked from the architecture knowledge base
- [x] #2 qgis-cli, qgis-plugin/qgis-sdk, qgis_rs, qgis_sdk, and qgis-sdk-bridge have distinct command and runtime responsibilities
- [x] #3 The shared qgis-protocol/qgis-engine reuse boundary and the qgis-sdk-core boundary are recorded
- [x] #4 The contract states that qgis-sdk does not directly depend on qgis-py and defines the optional acceleration route
- [x] #5 Canonical executable names, aliases, CLI/FFI responsibilities, and no-fallback policy are explicit
- [x] #6 Implementation tasks reference the refactor and TDD skill rules and preserve existing public behavior
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-04: the contract already existed as doc-7 and D13; what this session added is the part a decision record cannot do for itself — enforcement, links, and an honest list of where the tree still disagrees.

AC#1: the capability ownership matrix (doc-7) is reviewed and linked from .knowledge/architecture.md by section anchor, alongside D13; .knowledge/INDEX.md now says D01–D13 rather than D01–D12.

AC#2–#5: recorded in D13 sections 1–5, and four of those rules are now decided by `pixi run xtask check-boundaries`, which runs in the gate with the other repo lints (D10: automation is an xtask subcommand, not a script). The rules read the manifests themselves: qgis-sdk must not depend on qgis-py; qgis-py and qgis-node declare no [[bin]]; qgis-cli, qgis-plugin and qgis-sdk each have exactly one declaring crate (cargo resolves every bin to the same target/<profile>/<name>, which is how a binding stub once shadowed the real binary); and any new *fallback* file under crates/, py-packages/ or ts-packages/ fails unless it is in TRACKED_FALLBACKS with the task that removes it. 11 tests in crates/xtask/tests/boundaries.rs cover the parsers and every rule in both directions, including one that asserts this repository obeys its own contract and one that asserts discovery still finds the crates the rules name — a rule that silently matches nothing passes forever.

Two deviations found and written into D13 rather than quietly checked off: py-packages/qgis-sdk/src/qgis_sdk/_fallback_cli.py still exists and is imported by qgis_sdk.cli when qgis_sdk._core is missing (allowlisted, TASK-43 pays it off), and py-packages/qgis-sdk ships a qgis-cli console script that shadows the canonical binary on PATH (TASK-44 reconciles it). D13 also now states what the gate cannot decide: behaviour behind a binary, console-script shadowing, and whether host wrappers stay thin.

AC#6: all five implementation tasks reference both skills — task-42 listed only the TDD skill and now lists the refactor skill too (via the backlog CLI, not a hand edit). Public behaviour is preserved: the only runtime change in this task is a new xtask subcommand; no existing command, API or output changed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
doc-7 is the accepted implementation contract, recorded as D13, linked from the architecture knowledge base by matrix anchor, and — for the four parts of it that are facts about manifests — enforced by `pixi run xtask check-boundaries` in the gate, with 11 tests behind it. Where the tree disagrees with the contract today, the disagreement is named with the task that fixes it (the surviving qgis_sdk fallback CLI, TASK-43; the SDK distribution shipping a qgis-cli console script, TASK-44) instead of being checked off. The downstream tasks 41, 42, 43, 44 and 26 all reference the refactor and TDD skill rules.
<!-- SECTION:FINAL_SUMMARY:END -->
