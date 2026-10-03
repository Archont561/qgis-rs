---
type: Decision
id: D12
title: "QGIS Native Manager over the C ABI"
description: "Keep QGIS objects on one dedicated owner thread, keep qgis-protocol as the normative wire contract, use path-based artifacts, and defer crash isolation to a later subprocess transport."
status: accepted
tags: [qgis, ffi, c-abi, cpp, protocol, threading, architecture]
date: 2026-10-03T00:00:00Z
---

# D12: QGIS Native Manager over the C ABI

## Context

RFC 19 replaces a growing per-concept CXX bridge with one native boundary:

```c
char *qgis_invoke(const char *request_json);
void qgis_free(char *buffer);
unsigned qgis_transport_version(void);
```

Phase 1 already shipped the Rust-side transport in `qgis-protocol` and
`qgis-engine`. The Python and Node binding crates each expose one JSON invoke
function, and the wire is `snake_case` throughout. The remaining phases put
QGIS state behind the same envelope, so the manager must preserve QGIS/Qt
thread affinity while sharing one contract with Rust and the language clients.

The current `qgis-sys` CXX shims and the tests in `crates/qgis-sys/tests/` are
useful implementation references, but they are not the RFC 19 boundary. D05's
single-threaded QGIS constraint remains the lower-level safety invariant; this
record chooses how the C ABI presents that constraint to callers.

This decision applies to the standalone/headless QGIS backend described by
RFC 19. QGIS desktop plugin runtime and UI code remains a host-owned PyQGIS/
Qt boundary, not an implicit second user of this manager.

## Decision

### 1. Concurrency: one dedicated QGIS owner thread and a blocking queue

The manager uses one dedicated single-threaded executor/owner rather than only
a global mutex. In a standalone process, the owner is the thread which creates
the manager's `QgsApplication` before any other Qt object (normally the
process's QGIS/Qt main thread); it is not an arbitrary worker thread created
after a host application already exists. Foreign callers feed that owner via
a blocking request queue. All QGIS objects, the ID registry, and all calls
into QGIS live on that owner. `qgis_invoke` is synchronous to callers, but its
work is represented as copied request bytes queued to the owner, and the
caller waits for the copied response. The response is then copied into the
manager-owned C buffer returned by `qgis_invoke`.

The invariants are:

1. No `QObject`, QGIS handle, Qt value with affinity, registry entry, or raw
   pointer crosses the queue. Queue messages contain UTF-8 JSON and plain
   response state only.
2. The owner thread is the only thread allowed to initialize or shut down
   `QgsApplication`, access the registry, or call QGIS. A global mutex may be
   used to protect non-QGIS bookkeeping, but it is not the concurrency model
   and must not be used as a substitute for owner-thread affinity.
3. `qgis_transport_version` performs no QGIS work and may answer without
   entering the queue. `qgis_invoke` copies the request before the caller's
   pointer can become invalid and never retains a caller-owned pointer.
4. A reentrant invoke from the owner thread must not wait on its own queue. The
   manager either dispatches that call directly under the same operation
   context or returns a structured `reentrant_call` error; it must never
   deadlock.
5. Initialization is explicit and one-time. The manager is a standalone
   headless QGIS owner, uses `QgsApplication` with GUI disabled, and refuses a
   conflicting second application rather than silently creating another
   singleton. Embedding into a process which already owns QGIS requires an
   explicit host-thread integration design and is outside RFC 19.
6. Shutdown drains or rejects queued work before releasing registry entries
   and the QGIS application. An abandoned registry entry is released by the
   owner during manager teardown.

A mutex around `qgis_invoke` was rejected. It serializes calls, but it does not
make an arbitrary sequence of caller threads the thread owning `QgsApplication`
or the QGIS objects. It also makes the safety of future rendering and event-
driven operations depend on every caller obeying an undocumented thread rule.
The queue makes the affinity rule structural and leaves the C ABI safe for
concurrent language clients without exposing QGIS objects to them.

QGIS is not made generally thread-safe by this choice. Parallel work may be
performed only on extracted plain data outside the manager, and any operation
that touches a QGIS object remains serialized on the owner thread.

### 2. Protocol ownership: `qgis-protocol` is the normative contract

`crates/qgis-protocol` remains the single source of truth for the transport
version, envelope fields, closed operation set, error-kind spellings, and
wire naming. It stays independent of `qgis-render`; domain payloads are not
copied into a second binding crate merely to make the C++ side convenient.

The shared contract has two layers:

- Rust types and serde behaviour in `qgis-protocol` are the normative
  implementation of the envelope and operation identifiers.
- A versioned JSON Schema artifact emitted from that crate is the
  language-neutral review and conformance artifact for the C++ manager. It is
  checked in under `crates/qgis-protocol/schema/` when the manager is
  implemented. The C++ side may use generated constants or hand-written
  `QJsonObject` accessors, but it must not introduce a competing schema or
  spelling table. Protocol tests compare the manager's requests and responses
  with the same fixtures used by Rust, Python, and Node.

Adding a manager operation therefore requires the `Operation` variant and
serde spelling, its payload/result schema, the generated schema artifact, the
C++ dispatch arm, and boundary conformance tests. A C++ operation that is not
represented in `qgis-protocol` is not part of the supported transport.

`transport_version` is the numeric envelope version and is checked before an
operation is dispatched. Version 1 accepts exactly version 1; an unsupported
version returns an error envelope containing `supported` and `received`, and
all responses echo the manager's supported version. A QGIS/render engine
release is separate from this transport version.

Every wire key and operation name is `snake_case`. The Rust serde derives and
protocol fixtures enforce that rule; the C++ manager uses the exact same keys
and does not accept camelCase aliases. JavaScript may rename fields only in
its host-language API at the edge. Python and the C ABI use the wire spelling
directly.

### 3. Binary artifacts: paths on the wire, metadata in the response

RFC 19 keeps rendered images and exported feature files path-based. The JSON
request supplies a path visible to the in-process manager, and the operation
writes the requested artifact there. The JSON response carries metadata such
as the resulting path, format, and byte count; it does not carry arbitrary
image or feature bytes as base64 or a large JSON array. Version 1 overwrites
an existing output path after validation; it does not promise atomic replacement.

The manager must validate the output path and format before touching QGIS,
write the artifact using the operation's documented overwrite/atomicity rules,
and never return a QGIS pointer as an artifact handle. The caller owns the
resulting filesystem path; manager shutdown does not delete it. Input and
output paths are local to the manager process because RFC 19 is an in-process
C ABI.

A future out-of-process transport may use a shared filesystem, an artifact
handle, or a streamed byte operation, but that is a separate protocol decision
and cannot silently change the meaning of version 1. The path policy is thus
explicit rather than an accidental consequence of the current MCP tool.

### 4. Crash isolation: out of scope for RFC 19 version 1

The manager catches C++ exceptions at every `extern "C"` boundary and turns
invalid JSON, unknown operations, invalid IDs, and QGIS-reported failures into
structured error envelopes. `qgis_free` is the only release function for
manager-owned response buffers. These rules prevent C++ exceptions and
allocation ownership mistakes from crossing the ABI.

They do **not** promise recovery from a segmentation fault, abort, memory
corruption, a QGIS/plugin crash, or an operating-system kill. In-process RFC
19 therefore does not provide crash isolation. The issue's informal
"never crash" wording means "never allow a C++ exception to cross this ABI"
only; it is amended by the issue update accompanying this ADR.

A later crash-isolated manager may run the same operation protocol over a
subprocess stdin/stdout transport. That later design must specify process
lifecycle, timeouts, artifact paths, and recovery, and must not be smuggled
into the C ABI implementation as an undocumented fallback.

### 5. Naming amendment for RFC 19

The examples in issue #19 were written before phase 1's shipped protocol and
use camelCase keys such as `transportVersion`, `layerId`, `isValid`, and
`featureCount`, plus dotted operation examples such as `layer.open`.
Those examples are illustrative only and are amended to the shipped contract:

```json
{
  "transport_version": 1,
  "operation": "layer_open",
  "payload": { "uri": "points.gpkg", "provider": "ogr" }
}
```

The corresponding result uses `layer_id`, `is_valid`, and
`feature_count`. Future RFC 19 operations use underscore-delimited
snake_case identifiers (`layer_open`, `layer_info`, `layer_close`,
`layer_features`), are added to the closed `Operation` enum, and are covered
by the shared fixtures. There are no wire-level camelCase aliases.

## Consequences

### Accepted

- QGIS state has one owner, so concurrent callers cannot move a QGIS object
  between threads by merely acquiring a mutex on different caller threads.
- The Python, Node, Rust, and C++ paths continue to share one versioned
  transport and one error vocabulary.
- Large binary results do not inflate the C heap response or require base64
  encoding; callers can consume the path with their normal filesystem APIs.
- A later subprocess implementation can reuse the operation envelope without
  pretending that the in-process ABI already isolates crashes.

### Costs

- Every manager call pays queue synchronization and one JSON parse/serialize
  pair, even when a caller is already on the owner thread.
- The manager is a serialized QGIS backend. Parallelism requires extracting
  plain data or starting separate isolated processes, not sharing registry IDs.
- The schema artifact and conformance fixtures become release obligations when
  a new operation is added.
- A caller cannot use RFC 19 to attach arbitrary existing desktop QGIS objects
  to the manager. That integration needs an explicit host-thread API later.

## Alternatives rejected

| Alternative | Reason rejected |
| --- | --- |
| One global mutex around `qgis_invoke` | Serializes calls but does not preserve QGIS/Qt thread affinity when callers differ. |
| Caller-thread execution with a documented mutex rule | Makes correctness depend on every embedding language and caller obeying a hidden owner-thread contract. |
| A second hand-maintained C++ schema | Drifts from Rust operation names and error spellings; conformance must consume the `qgis-protocol` contract. |
| Inline base64 or arbitrary bytes in the envelope | Expensive for images/features and changes the memory/backpressure profile of a JSON ABI. |
| In-process signal/exception recovery for crashes | Catches C++ exceptions only; it cannot safely recover from memory corruption or a segfault. |
| A subprocess as part of RFC 19 v1 | Valuable later, but it changes lifecycle and filesystem semantics and needs its own timeout/restart contract. |

## Implementation gates for RFC 19 phases

- **Phase 2 (`TASK-25.1`)** must implement and test the owner executor,
  concurrent callers, initialization/shutdown, ID registry ownership, the
  three C exports, and the exception/free-pair rules. It must not implement a
  mutex-only manager.
- **Phase 3 (`TASK-25.2`)** must add `layer_open`, `layer_info`,
  `layer_close`, and batched `layer_features` as closed protocol operations
  with shared snake_case fixtures and no raw pointers on the wire.
- **Phase 4 (`TASK-25.3`)** must keep render/export outputs path-based,
  return artifact metadata, and make capability reporting reflect the live
  backend without claiming crash isolation.
- The manager conformance suite must run against the same transport version,
  operation names, error kinds, and JSON fixtures as the Rust engine and host
  clients.

## References

- [RFC 19](https://github.com/Archont561/qgis-rs/issues/19)
- [D05 — Threading Model](D05-threading.md)
- [D06 — String Strategy](D06-string-strategy.md)
- [D09 — Wire Protocol over FFI](D09-wire-protocol-over-ffi.md)
- [QgsApplication API](https://api.qgis.org/api/classQgsApplication.html)
- [Qt Threads and QObjects](https://doc.qt.io/qt-6/threads-qobject.html)
