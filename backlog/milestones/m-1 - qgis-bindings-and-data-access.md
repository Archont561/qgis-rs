---
id: m-1
title: "QGIS Bindings and Data Access"
---

## Description

Incremental qgis-sys bindings, safe-wrapper foundations, structured errors, and data-access validation.

Primary task: TASK-5.

**Superseded.** TASK-6 through TASK-9 bound QGIS concept by concept through a `cxx::bridge`. RFC 19 replaced that boundary with the native manager and one C ABI, D12 recorded the decision, and no `cxx::bridge` remains in the repository — so those four were archived on 2026-10-04 as superseded rather than deferred. TASK-5 shipped before the change and stays Done. The work they described now arrives as native-manager operations; see m-0 and TASK-30.
