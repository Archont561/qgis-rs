# Cross-language QGIS bridge test contract

**Status:** normative, version 1 · **Owner:** TASK-31 · **Fixtures:** [`test-fixtures/bridge/`](/test-fixtures/bridge/)

The *bridge* is the seam between a plugin's web UI and its Python host: a QWebChannel
endpoint on one side, `@qgis-sdk/bridge` on the other. It is **not** the engine transport
(`crates/qgis-protocol`, `transport_version`), which is in-process Rust ↔ binding. Two wires,
two version numbers, deliberately — but one set of conventions, because a developer who has
read one should not be surprised by the other.

This document is the contract Python and TypeScript test suites consume. It is a *testing*
contract first: every rule below has a fixture in `test-fixtures/bridge/` and a test in at
least two languages, so a rule that drifts goes red somewhere instead of being re-decided.

## 1. Four namespaces, not one object

A bridge target is one of four kinds, and the kind decides what a test may assume:

| `kind` | Target | What it is | What a test may assume |
| --- | --- | --- | --- |
| `engine` | `engine` | Pure calls answered by the Rust engine — geometry, tiles, CRS, project metadata | Deterministic; no QGIS, no Qt, no UI. Safe in a pure unit test |
| `qgis_host` | `qgis` | Calls that need a live QGIS: layers, project, processing, task manager, message bar | Requires the QGIS environment; a pure test must **skip**, never fake a green |
| `plugin` | `<plugin_name>` | Methods a plugin itself exposes to its own web UI | Defined by the plugin's own manifest; nothing is built in |
| `ui` | `ui` | Stateful UI operations and the events they emit — dialogs, docks, progress, theme | Stateful and ordered; results are acknowledgements, the payload arrives as an event |

`engine` and `qgis` are distinct targets on purpose: the same word ("layers") means a
registry lookup in one and a managed handle in the other, and a test that cannot tell them
apart cannot tell a missing QGIS from a wrong answer.

Namespacing is by **target**, not by method prefix. Method names are dotted and
`snake_case` (`layers.add_vector`), never camelCase; the JavaScript client renames at its own
edge exactly as it does for the engine transport (D09).

## 2. Envelopes

Version 1 of the bridge wire. Every envelope carries `bridge_version`.

```json
{ "bridge_version": 1, "request_id": "req-1", "target": "qgis", "method": "layers.list", "args": {} }
```

```json
{ "bridge_version": 1, "request_id": "req-1", "ok": true, "result": [] }
```

```json
{ "bridge_version": 1, "request_id": "req-1", "ok": false,
  "error": { "kind": "unknown_method", "message": "qgis has no method layers.teleport",
             "details": { "target": "qgis", "method": "layers.teleport" } } }
```

```json
{ "bridge_version": 1, "event": "task.progress", "target": "qgis",
  "request_id": "req-7", "payload": { "task_id": "task-3", "progress": 40.0 } }
```

Rules, each of them tested:

- **`request_id` is the caller's string and comes back unchanged** on success and on failure.
  It is opaque to the host: no ordering, no parsing, no reuse semantics. A response without
  the request's id is a protocol violation, not a late answer.
- **`ok` decides which field is present.** `ok: true` carries `result` and never `error`;
  `ok: false` carries `error` and never `result`. There is no third state and no `result`
  that means failure.
- **An event is not a response.** It has `event`, never `ok`. `request_id` is present only
  when the event belongs to a call in flight (task progress), absent otherwise (theme change).
- **`args` is an object**, always, even when empty — never positional, never null. The
  QWebChannel callback argument is the host's business, not the contract's.

## 3. Error kinds are a closed set

A client maps these onto its own language's exceptions; nothing matches on English prose.

| Kind | Meaning |
| --- | --- |
| `invalid_request` | The envelope is malformed: missing field, wrong type, unknown `bridge_version` |
| `unknown_target` | No such bridge object in this session |
| `unknown_method` | The target exists; the method is not in its manifest |
| `invalid_arguments` | The method exists; `args` does not satisfy its argument schema |
| `permission_denied` | The method exists and is callable, but the plugin lacks the permission it declares |
| `unknown_object` | An object handle is unknown, expired, or belongs to another session |
| `host_unavailable` | The call needs QGIS (or Qt, or a WebEngine view) and it is not there |
| `internal_error` | The handler raised. The message is for a human; `details` may carry a type name |

`host_unavailable` is the kind that keeps a missing environment from looking like a bug in
the plugin — and it is why a pure test suite can assert "this call is not answerable here"
instead of installing a fake QGIS.

## 4. Object handles are opaque and session-scoped

Anything the host cannot serialise whole — a layer, a dialog, a task — crosses as a handle:

```json
{ "object_id": "obj-9c1a", "object_type": "qgis.layer", "session_id": "sess-1" }
```

- `object_id` is **opaque**: a client may compare and echo it, never parse, derive or
  construct one. The fixtures deliberately use ids with no readable structure.
- A handle is **session-scoped**. Presenting it to another session is `unknown_object`,
  not a silent miss and not a fresh object.
- `object_type` is the handle's manifest type, dotted and `snake_case`, so a client can tell
  a `qgis.layer` from a `ui.dialog` without asking.

## 5. The manifest is the single source of methods

One manifest per target, versioned, in `test-fixtures/bridge/descriptions/`. It describes
methods, argument schemas, result schemas, permissions and events — and nothing else is
allowed to list them. A second spelling table in a binding, a doc page or a test is the
duplication this contract exists to prevent (AGENTS.md, DRY).

```json
{
  "bridge_version": 1,
  "namespace": "qgis",
  "kind": "qgis_host",
  "version": "1.0",
  "methods": [
    { "name": "layers.list", "call_kind": "qgis_host", "permissions": ["layer.read"],
      "args": { "type": "object", "properties": {}, "additional_properties": false },
      "result": { "type": "array", "items": { "type": "object" } } }
  ],
  "events": [
    { "name": "task.progress", "payload": { "type": "object",
      "properties": { "task_id": { "type": "string" }, "progress": { "type": "number" } },
      "required": ["task_id", "progress"] } }
  ]
}
```

Schemas use a **deliberately small** JSON-Schema subset — `type`, `properties`, `required`,
`items`, `enum`, `additional_properties`, and `$handle` for an object handle of a given type.
It is small because three languages have to agree on it offline, and because a schema
language rich enough to be interesting is one more thing to test.

## 6. The fixture tree

```text
test-fixtures/bridge/
├── cases.json          # the catalogue: every vector, its file, and what it must do
├── descriptions/       # one manifest per target: engine, qgis, plugin, ui
├── requests/           # well-formed requests, one per covered method
├── responses/          # success and error envelopes, correlated by request_id
├── events/             # event envelopes
└── malformed/          # envelopes that must be rejected, with the kind they must produce
```

`cases.json` is what the three suites iterate; it is the only list of files, so adding a
vector adds it to Rust, Python and TypeScript at once. Each case names the fixture file, its
category, and its expected outcome (`valid`, or the `error_kind` the host must answer with).

## 7. What each language tests, and what it must not share

Three suites, one set of files, **no shared fake implementation classes** — sharing the
observable contract is the point; sharing a fake would mean the two sides agree because they
are the same code.

- **Rust** — `crates/qgis-protocol/tests/bridge_contract.rs`. Types in
  `qgis_protocol::bridge` parse every manifest and every fixture; the subset validator checks
  each request against its manifest schema; malformed vectors must produce the stated kind.
  This is the gate that makes a hand-edited fixture fail CI.
- **Python** — `py-packages/qgis-sdk/tests/test_bridge_contract.py`, pure, no QGIS, no Qt. It
  reads the same files with `json` and asserts the conventions a router must honour:
  request-id correlation, the `ok`/`result`/`error` split, the closed kind set, snake_case
  wire names, handle opacity and session scope.
- **TypeScript** — `ts-packages/qgis-sdk-bridge/tests/bridge-contract.test.ts`, under `bun
  test`, no QWebChannel and no globals. Same files, client-side view: every manifest method
  yields exactly one proxy path, unknown methods fail predictably, events are not responses.

A suite may build its own fakes; it may not import another language's. The files in
`test-fixtures/bridge/` are the only thing in common.

## 8. Relationship to the engine transport

| | Bridge (this document) | Engine transport (`qgis-protocol`) |
| --- | --- | --- |
| Version field | `bridge_version` | `transport_version` |
| Addressing | `target` + dotted `method` | flat `operation` enum, closed |
| Failure | `ok:false` + `error.kind` from §3 | `ok:false` + `result.kind` from `ErrorKind` |
| Events | yes | no — request/response only |
| Handles | opaque session-scoped strings | integer layer ids in the manager registry |

`engine`-kind bridge methods are a thin forwarding of engine operations: the bridge adds
`request_id`, permissions and the event channel, and changes nothing about the payloads.
That is why the two version numbers stay separate — the engine can rev its envelope without
a plugin UI rebuild, and vice versa.
