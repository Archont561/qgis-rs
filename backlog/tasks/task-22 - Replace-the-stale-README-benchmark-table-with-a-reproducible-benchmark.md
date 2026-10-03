---
id: TASK-22
title: Replace the stale README benchmark table with a reproducible benchmark
status: To Do
assignee: []
created_date: '2026-10-02 22:35'
labels: []
dependencies: []
priority: low
type: task
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The root README still quotes render/tiling numbers against PyQGIS on an i7-12700K with no script behind them, while the only measured numbers in the repository are the per-call costs now quoted in ts-packages/qgis-node/README.md. Either delete the table or back it with a committed benchmark that anyone can run (`pixi run xtask bench`, criterion for the Rust side), and state the machine and the QGIS version it was produced on.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every published performance figure is produced by a command in the repository
- [ ] #2 The README states the hardware, the QGIS version and the date of the run
<!-- AC:END -->
