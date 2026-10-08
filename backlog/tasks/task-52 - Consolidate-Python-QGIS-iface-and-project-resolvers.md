---
id: TASK-52
title: Consolidate Python QGIS iface and project resolvers
status: Done
assignee: []
created_date: '2026-10-08 18:14'
updated_date: '2026-10-08 21:25'
labels:
  - python
  - bridge
  - refactor
dependencies: []
references:
  - py-packages/qgis-sdk/src/qgis_sdk/bridge/qgis_api/iface.py
  - py-packages/qgis-sdk/src/qgis_sdk/bridge/qgis_api/layers.py
  - py-packages/qgis-sdk/src/qgis_sdk/bridge/qgis_api/message.py
  - py-packages/qgis-sdk/src/qgis_sdk/bridge/qgis_api/project.py
  - py-packages/qgis-sdk/src/qgis_sdk/bridge/qgis_api/api.py
documentation:
  - >-
    backlog/docs/refactor/doc-3 -
    Repository-Refactor-and-Test-Modernization-Plan.md
  - .agents/skills/tdd/SKILL.md
  - .agents/skills/refactor/SKILL.md
priority: medium
type: task
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The built-in Python QGIS API repeats identical lazy optional-runtime resolvers. _get_project is copied in iface, layers, and project. _get_iface is copied in iface, layers, and message. Move only this environment-discovery policy behind one internal helper and preserve all API-specific behavior. This implements the runtime-boundary portion of P1.7 in the repository refactor plan.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Agree the public test seam with the user before adding tests. Exercise QgisApi host-call methods rather than testing the private _get_iface or _get_project helpers directly.
- [x] #2 Add behavior tests first for explicit iface injection precedence, lazy QGIS discovery, unavailable QGIS fallback, and project instance lookup using QGIS-free fakes.
- [x] #3 Extract one internal resolver implementation and use it from iface, layers, message, and project without changing public imports or API methods.
- [x] #4 Preserve lazy imports, the iface is not None override rule, None on ImportError, existing exception behavior, and each API method fallback.
- [x] #5 Run the QGIS-free qgis-sdk Python tests and the relevant Pixi package gate. Leave the task open until verified.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-08: The agreed public seam is QgisApi host-call methods. Added QGIS-free characterization tests before the resolver refactor for explicit iface precedence, falsey non-None injection, lazy discovery, unavailable-QGIS method fallbacks, QgsProject.instance lookup, and ImportError versus RuntimeError behavior.

2026-10-08: Extracted resolve_qgis_resource in the internal qgis_api resolver module and migrated iface, layers, message, and project. Kept API classes/imports/methods and per-method fallbacks intact; QGIS imports remain lazy and only ImportError becomes None.

2026-10-08: The first pure package run exposed an existing property-strategy bug: plugin_names could generate the reserved keyword for. Filtered Python keywords so the required package gate could pass.

2026-10-08 verification through Pixi: focused resolver tests passed; qgis-sdk pure gate passed with 405 passed, 3 skipped, 8 deselected; pixi run gates passed (repo checks, formatting, lint, full test fan-out, and pack checks).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Consolidated the built-in Python QGIS iface and project discovery behind one lazy internal resolver shared by iface, layers, message, and project. QGIS-free tests exercise QgisApi host calls for injected-iface precedence (including falsey values), deferred discovery, unavailable-runtime fallbacks, project singleton lookup, and exception semantics. Preserved public API surfaces and method-specific behavior. Fixed the pre-existing Python-keyword plugin-name strategy issue discovered by the pure gate. Verified with the qgis-sdk pure gate and the full Pixi gates.
<!-- SECTION:FINAL_SUMMARY:END -->
