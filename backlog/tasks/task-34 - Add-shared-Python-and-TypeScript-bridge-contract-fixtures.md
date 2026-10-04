---
id: TASK-34
title: Add shared Python and TypeScript bridge contract fixtures
status: To Do
assignee: []
created_date: '2026-10-03 09:16'
updated_date: '2026-10-04 12:48'
labels:
  - testing
  - bridge
  - protocol
  - cross-language
milestone: m-4
dependencies:
  - TASK-31
documentation:
  - >-
    backlog/docs/testing/doc-5 -
    QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md
  - .knowledge/testing.md
priority: high
type: task
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create the language-neutral test-fixtures/bridge tree and make Python and TypeScript consume the same bridge descriptions, requests, responses, errors, events, and known QGIS values. Keep fake implementations language-specific while making the observable wire contract identical.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Descriptions for bridge and qgis targets define methods, arguments, results, permissions, and events in one canonical format.
- [ ] #2 Canonical fixtures cover success, structured errors, malformed input, unknown target/method, event delivery, task progress, and object-handle behavior.
- [ ] #3 Python pytest/Hypothesis tests and TypeScript Bun/fast-check tests read the same fixture values.
- [ ] #4 Golden bridge values remain explicit examples and are not replaced by property tests.
- [ ] #5 A fixture validation command fails on unknown fields, missing request IDs, non-snake-case wire names, or incompatible schema versions.
<!-- AC:END -->
