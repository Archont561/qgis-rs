---
id: TASK-31
title: Define the cross-language QGIS bridge test contract
status: To Do
assignee: []
created_date: '2026-10-03 09:16'
updated_date: '2026-10-04 12:48'
labels:
  - testing
  - bridge
  - protocol
  - qgis-sdk
milestone: m-4
dependencies:
  - TASK-23
documentation:
  - >-
    backlog/docs/testing/doc-5 -
    QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md
  - >-
    backlog/docs/architecture/doc-4 -
    QGIS-Native-Manager-and-API-Coverage-Strategy.md
priority: high
type: task
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define the language-neutral bridge testing contract that Python and TypeScript utilities must consume. Specify bridge request, response, error, event, description, permission, and object-handle shapes. Keep engine operations and stateful UI bridge operations in separate namespaces while sharing versioning and error conventions.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A versioned bridge manifest describes methods, argument schemas, result schemas, permissions, and events.
- [ ] #2 Canonical request, success, error, event, malformed-input, and unknown-method fixtures exist in a language-neutral test-fixtures/bridge tree.
- [ ] #3 Request IDs, snake_case wire names, structured error kinds, and opaque session-scoped object IDs are specified and tested.
- [ ] #4 The contract explicitly distinguishes pure engine calls, QGIS host calls, plugin calls, and UI events.
- [ ] #5 Python and TypeScript test plans reference the same fixtures without sharing fake implementation classes.
<!-- AC:END -->
