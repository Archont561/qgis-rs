---
id: TASK-14
title: Implement declarative expression engine wrappers
status: To Do
assignee: []
created_date: '2026-09-30 20:49'
labels:
  - qgis-sdk
  - python
  - expressions
dependencies: []
documentation:
  - .knowledge/qgis-plugin-sdk.md
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement qgis_sdk.expr module providing fluent builders, tagged template string evaluation, and helper decorators for QGIS expression evaluation against features.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 evaluate(expression, feature, context) evaluates QGIS expressions safely
- [ ] #2 Helper for filter expressions on feature iterators
- [ ] #3 Fallback evaluation engine for pure Python testing
<!-- AC:END -->
