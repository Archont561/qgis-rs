---
id: TASK-30
title: Generate a versioned QGIS API manifest and manager handlers
status: To Do
assignee: []
created_date: '2026-10-03 08:57'
labels:
  - rfc
  - ffi
  - cpp
  - codegen
  - api
dependencies:
  - TASK-25.4
documentation:
  - >-
    backlog/docs/architecture/doc-4 -
    QGIS-Native-Manager-and-API-Coverage-Strategy.md
  - .knowledge/decisions/D12-qgis-native-manager-over-c-abi.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build the version-pinned extraction and generation pipeline described in the QGIS Native Manager and API Coverage Strategy. Read QGIS public headers together with binding/ownership metadata, normalize declarations into an explicit support manifest, and generate manager operation registrations, codecs, protocol metadata, documentation, and coverage reports. Start with core/data modules; keep GUI, private, provider-specific, and unsupported declarations explicit rather than silently dropping them.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The generator records every discovered public declaration as supported, supported_manual, partial, unsupported, host_only, provider_optional, or deprecated with a reason and QGIS version range.
- [ ] #2 The generated manifest produces compilable manager handlers/codecs and an api.describe capability report without introducing a second hand-written operation spelling table.
- [ ] #3 Ownership, invalidation, overload, enum, QVariant, binary-artifact, and paging mappings are explicit and have representative runtime tests.
- [ ] #4 Rust, Python, TypeScript, and C++ consume shared protocol fixtures for generated core operations and exact error envelopes.
- [ ] #5 A QGIS upgrade produces an API diff and fails review when declarations are silently dropped or ownership metadata changes.
<!-- AC:END -->
