---
id: TASK-52
title: Consolidate Python QGIS iface and project resolvers
status: To Do
assignee: []
created_date: '2026-10-08 18:14'
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
- [ ] #1 Agree the public test seam with the user before adding tests. Exercise QgisApi host-call methods rather than testing the private _get_iface or _get_project helpers directly.
- [ ] #2 Add behavior tests first for explicit iface injection precedence, lazy QGIS discovery, unavailable QGIS fallback, and project instance lookup using QGIS-free fakes.
- [ ] #3 Extract one internal resolver implementation and use it from iface, layers, message, and project without changing public imports or API methods.
- [ ] #4 Preserve lazy imports, the iface is not None override rule, None on ImportError, existing exception behavior, and each API method fallback.
- [ ] #5 Run the QGIS-free qgis-sdk Python tests and the relevant Pixi package gate. Leave the task open until verified.
<!-- AC:END -->
