---
id: TASK-42
title: Stabilize Python and Node FFI client contracts
status: To Do
assignee: []
created_date: '2026-10-03 09:35'
updated_date: '2026-10-10 13:52'
labels:
  - ffi
  - python
  - node
  - typescript
  - testing
milestone: m-3
dependencies:
  - TASK-40
  - TASK-31
documentation:
  - >-
    backlog/docs/architecture/doc-7 -
    Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md
  - py-packages/qgis-py/README.md
  - ts-packages/qgis-node/README.md
  - .knowledge/decisions/D09-wire-protocol-over-ffi.md
  - .knowledge/decisions/D12-qgis-native-manager-over-c-abi.md
  - .knowledge/decisions/D13-rust-cli-ffi-and-qgis-sdk-boundaries.md
  - .knowledge/decisions/D15-qgis-sdk-cli-pure-python-typer.md
  - >-
    backlog/docs/testing/doc-5 -
    QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md
  - .agents/skills/tdd/SKILL.md
  - .agents/skills/refactor/SKILL.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Current contract
Keep qgis-py and @archont561/qgis-node thin standalone-engine clients under D09, D12 and D13. Native addons expose the shared JSON invoke boundary and transport-version introspection; ergonomic objects and typed errors live in the host-language wrappers. Shared protocol definitions and fixtures own operation names, capabilities, errors, paging/cursors, artifact metadata and defined cancellation outcomes. No QGIS class hierarchy or CLI argv semantics is mirrored in the addons.

## Scope
Audit the shipped adapters and wrappers before adding work: both Rust adapters already export invoke and transport_version, and existing Python/Node tests cover shared wire behavior. Record which criteria those tests prove and add missing public-seam cases, rather than treating unchecked task boxes as proof that nothing exists. Preserve current exported host-language naming conventions and the raw invoke escape hatch.

Large results remain bounded pages/cursors or path-based artifacts where the protocol defines them. Unsupported capabilities and unavailable native backends must remain explicit structured responses, not silent Python/JavaScript fallback semantics. No raw pointer, live Qt/QGIS object or QVariant crosses the serialized boundary; opaque manager IDs are not raw pointers.

## Scope retired on 2026-10-10
CLI launcher implementation and launcher-process tests are no longer deliverables of this task. The built-in Python/Node CLI paths were removed in 47a909a/41b02b4; the Node executable distribution is handled by TASK-58. Do not recreate an argparse/citty wrapper, a second parser, a run_cli native API, or a Python executable merely to satisfy former AC5. Canonical qgis-cli command behavior belongs to TASK-41; optional binary distribution remains packaging work, not FFI semantics.

TASK-43 owns the hosted SDK dependency/ownership boundary; TASK-63 owns the reverse import probe and its compatibility decision. This task does not introduce SDK acceleration, resolve those separate policies, or change the shared protocol merely to make fixtures pass.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each native addon retains invoke(request_json) plus transport-version introspection as its stable native callable surface, preserving existing host-language naming and metadata exports. No per-QGIS-class native API or CLI argv dispatcher is introduced.
- [ ] #2 Python and TypeScript clients consume shared protocol fixtures for capabilities, structured errors, transport mismatch, pages/cursors and artifact metadata, including cancellation outcomes where defined. Existing coverage and missing cases are audited against the protocol; no independent per-binding wire vocabulary or unsupported capability is invented.
- [ ] #3 Host-language wrappers map structured error kinds without matching English error text, preserve contextual details, expose documented raw invoke escape hatches, and report unsupported operations or unavailable backends explicitly without alternate Python/JavaScript semantics.
- [ ] #4 Large-result client paths use bounded pages/cursors or artifact metadata as defined by the shared protocol. No raw QGIS/Qt pointer, live object or QVariant crosses the binding boundary; copied values and opaque manager IDs retain their documented ownership and lifetime rules.
- [ ] #5 FFI packages and native addons own no command parsing, argv dispatch or launcher implementation. Tests preserve removal of the built-in Python/Node CLI paths and do not recreate them; any separately distributed qgis-cli binary remains a packaging concern outside this task.
- [ ] #6 Focused Python, Node and cross-language fixture tests pass through the applicable existing pure/native Qt/QGIS gates, with no WebEngine requirement for pure operations. Tests remain under tests/, behavior changes follow agreed public seams and red-green slices, and exact evidence or environmental blockers accompany acceptance checks.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Scope split: the Node qgis-cli launcher is replaced by a binary download (TASK-58). The Python side has no argparse qgis-cli after the TASK-57 work.

2026-10-10 owner-approved scope update: renamed to FFI client contracts. Former AC5 (Python/npm launchers executing the canonical binary) is superseded by an explicit no-CLI-semantics boundary; AC6 no longer requires launcher tests. Existing adapter exports are visible in py-packages/qgis-py/src-rust/src/lib.rs and ts-packages/qgis-node/src-rust/src/lib.rs; this inspection is not acceptance proof for the full contract. Replaced the dangling crates/qgis-py/ARCHITECTURE.md reference with current package documentation. Status and TASK-40/TASK-31 dependencies remain unchanged; all replacement criteria remain unchecked. Earlier scope-split notes are historical, not instructions to restore removed launchers.
<!-- SECTION:NOTES:END -->
