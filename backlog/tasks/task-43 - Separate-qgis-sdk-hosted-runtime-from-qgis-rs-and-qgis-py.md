---
id: TASK-43
title: Enforce pure-Python qgis-sdk dependency and hosted-runtime boundaries
status: To Do
assignee: []
created_date: '2026-10-03 09:35'
updated_date: '2026-10-10 13:52'
labels:
  - qgis-sdk
  - python
  - ffi
  - architecture
  - refactor
milestone: m-3
dependencies:
  - TASK-40
documentation:
  - >-
    backlog/docs/architecture/doc-7 -
    Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md
  - .knowledge/decisions/D13-rust-cli-ffi-and-qgis-sdk-boundaries.md
  - .knowledge/decisions/D15-qgis-sdk-cli-pure-python-typer.md
  - .knowledge/qgis-sdk.md
  - py-packages/qgis-sdk/pyproject.toml
  - py-packages/qgis-sdk/tests/test_pure_python.py
  - py-packages/qgis-sdk/tests/test_cli_task57.py
  - .agents/skills/tdd/SKILL.md
  - .agents/skills/refactor/SKILL.md
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Current contract
Reconcile and enforce the hosted SDK boundary under D13 and accepted D15. The qgis-sdk distribution is pure Python, built with setuptools, with one typer CLI. Hosted plugin lifecycle, UI, Processing, tasks, feedback and QGIS object ownership stay with qgis_sdk/PyQGIS/PyQt. The base distribution has no required dependency on qgis-py or its native extension, and standalone qgis-py remains a separate product.

There is no Rust qgis-sdk crate, qgis_sdk._core, SDK acceleration adapter, or Rust scaffold/build surface to restore. Plugin authors who choose Rust manage their own library and build outside the SDK contract. Native qgis-py and Node addons retain their existing wire boundaries; SDK-owned QGIS/Qt objects must not cross into them as live objects or pointers.

## Scope and existing evidence
Audit the current manifests, imports, wheel contents, public exports and supported runtime tests against these boundaries; extend public-seam coverage only where missing. Inspection already finds setuptools and only typer/questionary runtime dependencies in py-packages/qgis-sdk/pyproject.toml, no Rust SDK crate, and retirement/import tests in tests/test_pure_python.py and tests/test_cli_task57.py. Those are evidence starting points, not blanket acceptance checks; record exact tests and remaining gaps before closing criteria.

Pure SDK tooling must remain usable without importing QGIS. Hosted features require QGIS explicitly and use its lifecycle/threading policy rather than silently creating a second standalone engine session. Optional SDK-side detection for an explicit hybrid workflow must not become a base installation/import requirement or an SDK-owned Rust acceleration implementation.

## Related work and non-goals
TASK-63 separately owns the reverse-direction qgis_py import of qgis_sdk and the still-open HAS_QGIS_SDK compatibility decision; do not make that decision here or duplicate its fix. TASK-42 owns shared FFI client contracts. Do not restore retired qgis_rs aliases, Rust tooling, or CLI launchers. This rewrite changes the task contract only, not package behavior.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The qgis-sdk base distribution declares no qgis-py dependency and its ordinary imports/tooling do not require or unconditionally import qgis_py or its native extension. Manifest and fresh-process import tests pin this boundary; any explicit SDK-side hybrid detection remains optional.
- [ ] #2 Hosted UI, Processing, plugin lifecycle, tasks, feedback and QGIS object ownership remain in qgis_sdk/PyQGIS/PyQt under the existing host lifecycle and thread-affinity contract. Supported hosted behavior neither silently creates a standalone engine session nor substitutes a fallback when QGIS is required.
- [ ] #3 The documented product split is verified: pure SDK tooling runs without QGIS or standalone bindings, while the qgis-py distribution does not require qgis-sdk as an installation dependency. The reverse-direction import probe and HAS_QGIS_SDK policy remain explicitly assigned to TASK-63, not implicitly checked off here.
- [ ] #4 The SDK wheel and public surface remain pure Python under D15: setuptools packaging, one qgis-sdk Python CLI, no native SDK extension or Rust SDK crate, and no SDK-owned Rust acceleration/scaffold/build commands. Existing retirement and CLI tests are retained or extended, not replaced with vacuous checks for deleted artifacts alone.
- [ ] #5 No SDK-owned live QGIS/Qt objects, raw pointers or QVariant values are handed across qgis_py native or Node NAPI boundaries. Supported cross-language integration uses the shared serialized protocol, copied values, opaque IDs or artifact metadata; TASK-42 owns the underlying FFI contract tests, with relevant evidence linked here.
- [ ] #6 Current supported imports and plugin lifecycle behavior remain covered without restoring removed aliases. Focused pure SDK tests, applicable Qt/QGIS hosted gates with offscreen serialized execution, and boundary checks pass; each checked criterion cites actual evidence and any environmental blocker stays open.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Names updated for the 2026-10 rename: the Python distribution is qgis-py and the Node package is @archont561/qgis-node. The qgis-rs compatibility alias is removed by TASK-60.

2026-10-10 owner-approved rewrite under D15. Former AC1 assumed a Rust SDK graph; AC3 used retired standalone naming; AC4 required an SDK-owned optional Rust acceleration adapter; AC5 named the deleted SDK extension and old Python alias. Those obligations are superseded by the six replacement criteria above, not completed by this edit. Earlier notes/comments are retained as historical context and are not the current contract. Status and dependencies remain unchanged; no AC is checked. TASK-63 retains its separate public-attribute decision.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-10-04 12:48
---
2026-10-04: dropped the TASK-36 dependency. TASK-43 is a dependency-boundary task under D13 - qgis_sdk never depends on qgis-py, and qgis_sdk._core stays optional tooling - while TASK-36 defines the declarative UI contract. The two are orthogonal: nothing in TASK-43 reads or changes the UI surface. The edge was blocking TASK-43, and TASK-44 behind it, on a task neither needs. TASK-40, which defines the product boundaries this task enforces, remains the real prerequisite and is Done.
---
<!-- COMMENTS:END -->
