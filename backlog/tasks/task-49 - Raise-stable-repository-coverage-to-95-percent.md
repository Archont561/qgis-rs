---
id: TASK-49
title: Raise stable repository coverage to 95 percent
status: To Do
assignee: []
created_date: '2026-10-06 20:11'
labels:
  - testing
  - coverage
  - quality
dependencies:
  - TASK-30
  - TASK-4
  - TASK-13
  - TASK-37
  - TASK-38
  - TASK-39
  - TASK-41
  - TASK-44
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After the architectural backlog settles the QGIS SDK UI, integration runner, PyQGIS wrappers, API manifest, CLI, FFI, runtime, and packaging boundaries, fix coverage measurement and raise stable production components toward 95 percent without testing obsolete internals or excluding difficult production code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Coverage inputs are current and reproducible offline, JavaScript coverage is persisted, and Codecov reports separate Rust Python SDK Python client JavaScript and native components
- [ ] #2 Codecov enforces at least 95 percent patch coverage for new and changed production lines without lowering the threshold through broad exclusions
- [ ] #3 Generated code embedded static templates and unreachable platform branches have explicit reviewed coverage policy; production behavior is not excluded merely because it is difficult to test
- [ ] #4 Stable components are raised in measured stages and repository-wide combined coverage reaches 95 percent with behavior tests at public seams
- [ ] #5 The full CI coverage lane and ordinary gates pass, and the final task notes reconcile local totals with the Codecov commit and component totals
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Run the offline coverage stage
- [ ] #2 Run pixi run gates
<!-- DOD:END -->
