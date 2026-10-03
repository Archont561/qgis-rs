---
id: TASK-40
title: 'Define Rust CLI, FFI, and QGIS SDK product boundaries'
status: To Do
assignee: []
created_date: '2026-10-03 09:35'
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
- [ ] #1 The capability ownership matrix is reviewed and linked from the architecture knowledge base
- [ ] #2 qgis-cli, qgis-plugin/qgis-sdk, qgis_rs, qgis_sdk, and qgis-sdk-bridge have distinct command and runtime responsibilities
- [ ] #3 The shared qgis-protocol/qgis-engine reuse boundary and the qgis-sdk-core boundary are recorded
- [ ] #4 The contract states that qgis-sdk does not directly depend on qgis-py and defines the optional acceleration route
- [ ] #5 Canonical executable names, aliases, CLI/FFI responsibilities, and no-fallback policy are explicit
- [ ] #6 Implementation tasks reference the refactor and TDD skill rules and preserve existing public behavior
<!-- AC:END -->
