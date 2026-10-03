---
id: TASK-16
title: Implement drop-in Rust acceleration for Python plugin hotspots
status: To Do
assignee: []
created_date: '2026-09-30 20:49'
updated_date: '2026-10-03 08:31'
labels:
  - qgis-sdk
  - rust
  - pyo3
  - performance
milestone: m-3
dependencies: []
documentation:
  - .knowledge/qgis-plugin-sdk.md
  - .knowledge/decisions/D07-rust-qgis-plugins.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the @rust_accelerated decorator and PyO3/maturin build scaffolding allowing Python plugins to seamlessly offload heavy feature/geometry processing to compiled Rust cdylibs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 @rust_accelerated decorator dynamically loads compiled Rust module if available, falling back to Python
- [ ] #2 Scaffold generator includes --rust flag creating a PyO3 workspace crate alongside plugin
- [ ] #3 Native and fallback parity tested
<!-- AC:END -->
