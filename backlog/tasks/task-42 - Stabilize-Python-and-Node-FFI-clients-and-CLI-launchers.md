---
id: TASK-42
title: Stabilize Python and Node FFI client contracts
status: To Do
assignee: []
created_date: '2026-10-03 09:35'
updated_date: '2026-10-10 17:01'
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

Evidence audit (2026-10-10, read-only; no source changed). Measured what already ships against each criterion so implementation starts from a baseline instead of re-deriving it.

AC1 — proven. Both addons expose exactly one callable plus transport introspection and nothing per-QGIS-class: py-packages/qgis-py/src-rust/src/lib.rs:28-40 (#[pyfunction] invoke, transport_version) and ts-packages/qgis-node/src-rust/src/lib.rs:21-39 (#[napi] invoke, transport_version). lib.rs:6-7 records the rule that a new capability is a qgis-engine operation, not a new pyfunction/napi export.

AC2 — partially covered, and the gap is breadth rather than soundness. test-fixtures/layer-lifecycle.json is genuinely shared: py-packages/qgis-py/tests/test_api.py:157 and ts-packages/qgis-node/tests/contract.test.js:188 both consume it, and crates/qgis-sys/tests/api_mappings.rs:95-125 (#![cfg(feature = "qgis")]) drives the real native manager with its requests and asserts the responses match, so the fixture is anchored to actual behaviour rather than self-consistent by construction. But it pins 4 of the protocol's operations, 1 of the 16 ErrorKind variants (invalid_object_id; see the error_kinds! block at crates/qgis-protocol/src/lib.rs:441-476), no capabilities case, and no artifact-metadata case for render_map/export_features. Cancellation is defined nowhere in crates/qgis-protocol or crates/qgis-engine, so this criterion's "where defined" clause is currently vacuous; record that rather than letting a later slice invent a cancellation contract.

AC3 — one concrete gap. Kind-based mapping without matching English prose is in place on both sides (_transport.py:89 _EXCEPTION_BY_KIND, commented "one kind cannot become two exception types"; index.js:73-80 EngineError carrying kind and detail), contextual detail is preserved, and the raw escape hatch is public in both (qgis_py __all__ includes "invoke"; ts-packages/qgis-node/src/index.d.ts:226). The gap: transport mismatch is implemented in both clients (_transport.py:131-138 raising TransportMismatch, index.js:89-95 throwing EngineError("unsupported_transport")) and no test in either language exercises it — grep over py-packages/qgis-py/tests/*.py and ts-packages/qgis-node/tests/*.js returns no TransportMismatch or unsupported_transport reference. Two shipped error paths are unexercised.

AC4 — structurally satisfied. The boundary is one JSON string in each direction, so no pointer, live object or QVariant can cross it; bounded pages (layer_features limit/next_offset) and path-based artifacts (RenderedMap) are used by both clients.

AC5 — strongly proven. A grep for argv, sys.argv, process.argv, argparse, click, typer, clap and Command::new across py-packages/qgis-py/src-rust/src, py-packages/qgis-py/python, ts-packages/qgis-node/src and ts-packages/qgis-node/src-rust/src returns nothing. py-packages/qgis-py/tests/test_no_cli.py pins no console_scripts or gui-scripts, no qgis_py.cli module and no _bin directory; ts-packages/qgis-node/tests/no-cli.test.js pins no bin, no optionalDependencies, no src/cli.js, no bin/, no scripts/stage-cli.js and no npm/ platform packages.

AC6 — tests are under tests/ in both packages and run in the existing gates (16 qgis-node tests, 18 qgis-py-dist tests at the 2026-10-10 baseline), with no WebEngine requirement for pure operations.

Two items need a decision before they can be implemented rather than audited: whether the shared fixture should grow to cover every ErrorKind and the artifact-metadata operations, and whether cancellation is in scope at all.
<!-- SECTION:NOTES:END -->
