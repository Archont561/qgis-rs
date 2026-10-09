---
id: TASK-31
title: Define the cross-language QGIS bridge test contract
status: Done
assignee: []
created_date: '2026-10-03 09:16'
updated_date: '2026-10-09 15:47'
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
- [x] #1 A versioned bridge manifest describes methods, argument schemas, result schemas, permissions, and events.
- [x] #2 Canonical request, success, error, event, malformed-input, and unknown-method fixtures exist in a language-neutral test-fixtures/bridge tree.
- [x] #3 Request IDs, snake_case wire names, structured error kinds, and opaque session-scoped object IDs are specified and tested.
- [x] #4 The contract explicitly distinguishes pure engine calls, QGIS host calls, plugin calls, and UI events.
- [x] #5 Python and TypeScript test plans reference the same fixtures without sharing fake implementation classes.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-04: the contract is written in `.knowledge/bridge-test-contract.md` (linked from the knowledge INDEX) and made executable in three places, all green on a restored sandbox.

AC#1 and AC#4: four versioned manifests in `test-fixtures/bridge/descriptions/` — `engine` (pure engine calls), `qgis` (QGIS host calls), `demo_plugin` (plugin calls) and `ui` (stateful UI and its events). Each method carries an argument schema, a result schema, a `call_kind` and its permissions; each manifest carries its events and their payload schemas. The schema language is a deliberately small JSON-Schema subset — `type`, `properties`, `required`, `items`, `enum`, `additional_properties`, `$handle` — because three languages have to agree on it offline and a richer one is one more thing to test. The namespaces are targets, not method prefixes: `engine.extent.describe` and `qgis.layers.list` are answered by different things, and a test that cannot tell them apart cannot tell a missing QGIS from a wrong answer.

AC#2: 6 requests, 10 responses (4 success, 6 error), 3 events and 12 malformed vectors, with `cases.json` as the catalogue — the only list of files, so one vector added there is checked by all three suites with no edit to any of them. The malformed set covers both halves of "unknown": `unknown_method` (including the camelCase spelling of a method that does exist) and `unknown_target`, plus a missing `request_id`, an unknown `bridge_version`, positional `args`, four argument-schema violations and two handle violations.

AC#3: `qgis_protocol::bridge` holds the envelope types and `validate_request`, the smallest implementation of the dispatch rules that can tell the twelve refusals apart in the order a host must check them — envelope, version, target, method, permissions, arguments. `crates/qgis-protocol/tests/bridge_contract.rs` drives the catalogue through it: 14 tests, two of them proptest properties (a `request_id` is echoed unchanged; no unlisted method ever dispatches). Error kinds are a closed enum whose wire spellings are cross-checked against the catalogue's list in both directions, so a kind added to one and not the other goes red. Handles are `{object_id, object_type, session_id}`, opaque and session-scoped: the rstest matrix proves the same id in another session, or under another type, is `unknown_object`.

AC#5: `py-packages/qgis-sdk/tests/test_bridge_contract.py` (46 passed, 2 skipped; pure Python, no QGIS, no Qt) and `ts-packages/qgis-sdk-bridge/tests/bridge-contract.test.ts` (part of the bridge package's 68 bun tests; no QWebChannel, no globals) read the same files from `test-fixtures/bridge/`. Neither imports the other's fakes, and neither imports a fake from Rust: what is shared is the observable contract, because two sides that agree by being the same code have not agreed about anything. The Python suite asserts the host's half (what a router must honour before it calls a handler), the TypeScript suite the client's half (one callable path per manifest method, the snake_case wire under a camelCase surface, correlation by `request_id` alone, an event that is never an answer).

Not implemented here, on purpose: no Python `BridgeRouter` and no TypeScript `BridgeHarness` — those are TASK-32 and TASK-33, and they now have fixtures to be built against rather than a prose spec. The engine transport is untouched; `bridge_version` and `transport_version` stay separate numbers, which is the point of §8 of the contract.

Path update: the bridge contract tests move to ts-packages/qgis-sdk with the package rename in TASK-56.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The bridge test contract is specified, fixtured and enforced. One normative document, four versioned manifests, 31 fixture vectors catalogued in `cases.json`, and three suites — Rust, Python, TypeScript — reading the same files and sharing no implementation. Every acceptance criterion is proved by a test that runs in `pixi run gates`, not by prose.
<!-- SECTION:FINAL_SUMMARY:END -->
