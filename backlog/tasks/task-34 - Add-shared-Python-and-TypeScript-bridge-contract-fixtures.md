---
id: TASK-34
title: Add shared Python and TypeScript bridge contract fixtures
status: Done
assignee:
  - '@me'
created_date: '2026-10-03 09:16'
updated_date: '2026-10-06 07:02'
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
- [x] #1 Descriptions for bridge and qgis targets define methods, arguments, results, permissions, and events in one canonical format.
- [x] #2 Canonical fixtures cover success, structured errors, malformed input, unknown target/method, event delivery, task progress, and object-handle behavior.
- [x] #3 Python pytest/Hypothesis tests and TypeScript Bun/fast-check tests read the same fixture values.
- [x] #4 Golden bridge values remain explicit examples and are not replaced by property tests.
- [x] #5 A fixture validation command fails on unknown fields, missing request IDs, non-snake-case wire names, or incompatible schema versions.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Keep test-fixtures/bridge/cases.json as the sole catalogue already consumed by Python, TypeScript, and Rust contract suites. Add an xtask validator at the repository automation seam, wire it into repo lints, and prove rejection of unknown fields, missing request IDs, non-snake-case wire names, and incompatible versions.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-06: Started. Confirmed seams: Python fixture loader/validator, TypeScript contract-fixtures API, and repository xtask fixture-validation command. Existing golden JSON remains the independent source of truth.

2026-10-06: The shared tree already contained canonical descriptions, successful and malformed requests, responses/errors, events/task progress, handles, and explicit golden values from TASK-31/TASK-33; Python Hypothesis and TypeScript fast-check suites both discover those values through cases.json. Added validate-bridge-fixtures as an xtask command and repo lint with strict catalogue, description, schema, request, response, and event parsing.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the shared bridge-contract fixture gate. cases.json remains the one catalogue consumed by Python, TypeScript, and Rust. The new xtask validator rejects structural drift, unknown fields, missing or mismatched request IDs, non-snake-case canonical wire names, incompatible bridge versions, invalid catalogue links, and inconsistent response/event envelopes; the validator now runs in the fast repo-lint stage.
<!-- SECTION:FINAL_SUMMARY:END -->
