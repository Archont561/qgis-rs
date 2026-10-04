---
id: m-2
title: "Project, Editing, and Rendering"
---

## Description

Project ownership, edit-buffer transactions, direct rendering, QGIS Server integration, and RFC 19 layer/render operations.

Primary tasks: TASK-19, TASK-25.2, TASK-25.3.

**Partly superseded.** TASK-10 through TASK-12 bound `QgsProject`, the edit buffer and the map renderer through the `cxx::bridge` RFC 19 removed; they were archived on 2026-10-04. Their functional equivalents shipped behind `qgis_invoke` instead — layer open/info/close and batched features in TASK-25.2, `render_map` and `export_features` in TASK-25.3. Transactional editing has no native-manager equivalent yet and is unclaimed work.
