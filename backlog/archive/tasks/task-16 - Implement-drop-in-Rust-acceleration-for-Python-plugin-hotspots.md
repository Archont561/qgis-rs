---
id: TASK-16
title: Implement drop-in Rust acceleration for Python plugin hotspots
status: To Do
assignee: []
created_date: '2026-09-30 20:49'
updated_date: '2026-10-10 09:22'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Archived 2026-10-10 as superseded by D15 section 3 as amended, on the owner decision recorded in this session.

All three acceptance criteria are premised on a feature the package does not have. AC1 asks for a rust_accelerated decorator that dynamically loads a compiled Rust module and falls back to Python. AC2 asks the scaffold generator for a rust flag creating a PyO3 workspace crate alongside the plugin. AC3 asks for native and fallback parity testing.

Measured today: zero occurrences of rust_accelerated and zero of HAS_RUST anywhere under py-packages or crates. There is no render.py, features.py, geometry.py or crs.py in qgis_sdk. TASK-57 removed with_rust from scaffold.py together with the Cargo and pyo3 template and its call site, and removed the rust subcommand group, every rust flag and the cargo passthrough from the CLI.

D15 section 3 as amended states that qgis-sdk contains no Rust, so the plugin CLI does not build a crate, and that a plugin wanting Rust runs cargo itself. That leaves no SDK surface for this task to implement: the decorator, the scaffold flag and the parity harness are all ruled out by the accepted decision, not merely unbuilt.

The specification text that still described this feature is being retired in TASK-64: .knowledge/qgis-sdk.md section 2 and its evidence-table row naming this task as the owner, plus docs/src/content/docs/guides/plugin-development.mdx.
<!-- SECTION:NOTES:END -->
