---
id: TASK-63
title: Stop qgis_py importing qgis_sdk at import time
status: To Do
assignee: []
created_date: '2026-10-09 21:44'
labels:
  - bug
  - qgis-py
  - boundaries
milestone: m-0
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Audit finding (session audit). py-packages/qgis-py/python/qgis_py/__init__.py lines 63-69 import qgis_sdk inside a try block to set HAS_QGIS_SDK. This makes the standalone qgis-py package depend at import time on the separate SDK distribution, and D13 requires the two to stay independent. The boundary checker does not inspect Python imports, so nothing flags it.

Decision (user, during audit): remove the probe. The hybrid workflow must be detected from the SDK side, not from qgis_py.

Behavior to change: importing qgis_py no longer imports qgis_sdk. Contract note: HAS_QGIS_SDK is listed in qgis_py.__all__, so it is public. Removing it is a contract change. Record in this task, before the fix commit, whether it is removed or kept as a deprecated attribute that is always False.

Non-goals: changing the qgis-sdk package; changing any other qgis_py export.

Bug-fix workflow: write the red test first, commit it separately, then the fix in its own commit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Red test first: importing qgis_py does not import qgis_sdk, checked through sys.modules in a fresh subprocess, observed failing before the fix
- [ ] #2 The fix removes the import from qgis_py and lands in a separate commit after the red test
- [ ] #3 The HAS_QGIS_SDK contract decision is recorded in this task before the fix commit, and __all__ matches it
- [ ] #4 The hybrid workflow still works: qgis_sdk detects qgis_py when both are installed, and a test covers it from the SDK side
- [ ] #5 Gates pass, and the D13 boundary note records that qgis-py must not import qgis-sdk
<!-- AC:END -->
