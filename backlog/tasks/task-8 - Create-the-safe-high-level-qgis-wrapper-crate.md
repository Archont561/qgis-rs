---
id: TASK-8
title: Create the safe high-level qgis wrapper crate
status: To Do
assignee: []
created_date: '2026-09-30 20:48'
updated_date: '2026-10-03 18:36'
labels:
  - qgis
  - architecture
  - api
  - deprecated
milestone: m-1
dependencies:
  - TASK-7
documentation:
  - .knowledge/decisions/D01-two-crate-architecture.md
  - .knowledge/architecture.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Establish the high-level safe qgis crate implementing RAII wrappers around qgis-sys types, enforcing !Send + !Sync single-threaded affinity (D05) and D01 crate separation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 New crate crates/qgis created and wired to workspace Cargo.toml
- [ ] #2 Application safe RAII guard handles init/exit lifecycle
- [ ] #3 VectorLayer, Fields, Feature, Geometry, Crs safe wrappers provided
- [ ] #4 VectorLayer::features(&self) implements Rust impl Iterator<Item = Feature>
- [ ] #5 All wrappers enforce !Send + !Sync via PhantomData<*const ()>
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Arena agent
created: 2026-10-03 18:36
---
Deprecated: superseded by RFC 19 native-manager operations; this legacy direct qgis-sys shim path is no longer planned.
---
<!-- COMMENTS:END -->
