---
id: TASK-30
title: Generate a versioned QGIS API manifest and manager handlers
status: In Progress
assignee: []
created_date: '2026-10-03 08:57'
updated_date: '2026-10-03 19:44'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03: Started the first vertical slice with a version-pinned core/data manifest at `crates/qgis-sys/native_manager/generated/api_manifest.json`. It records explicit declaration statuses, QGIS version ranges, ownership, operation/handler mappings, exclusions, and representative mapping policies.

2026-10-03: Added `pixi run xtask api-manifest [--check] [--diff-against PATH]` implementation. It validates manifest status/reason/version invariants, rejects dropped declarations/operations and ownership changes during upgrades, and deterministically generates the native-manager operation table and manifest-version header.

2026-10-03: Native `engine_info` now advertises manifest metadata, and `api_describe` routes through the generated handler registry. Cross-language/runtime gates and the full clang-AST extraction/API-diff pipeline remain outstanding; keep this task In Progress until Pixi/QGIS validation is available.
<!-- SECTION:NOTES:END -->
