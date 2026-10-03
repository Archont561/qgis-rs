---
id: doc-4
title: QGIS Native Manager and API Coverage Strategy
type: specification
created_date: '2026-10-03 09:10'
---

# QGIS native manager and API coverage strategy

## Executive decision

Do not hand-write a C++ wrapper and JSON operation for every QGIS class. That path will duplicate QGIS's type system, ownership rules, overloads, and version churn, and it will never give a trustworthy meaning to “all QGIS API”.

Use two related products behind the current D09/D12 boundary:

1. **A small native manager runtime** — one QGIS owner thread, one generational object registry, one JSON envelope, one generated operation registry, and one C ABI.
2. **A generated API coverage pipeline** — QGIS headers plus QGIS binding metadata become a versioned manifest, codecs, handlers, host-language protocol types, documentation, and coverage reports.

The manager is the runtime. The generator is how the runtime grows. A supported API is an entry in the generated manifest with a known type mapping, ownership rule, version range, and test; a declaration that merely exists in a QGIS header is not automatically supported.

This extends, rather than replaces, [D12 — QGIS Native Manager over the C ABI](../../../.knowledge/decisions/D12-qgis-native-manager-over-c-abi.md). D12 remains authoritative for the owner thread, `qgis-protocol`, path-based artifacts, and the absence of in-process crash isolation.

## What “all QGIS API” means

QGIS has several different surfaces. They cannot all share one lifecycle or one serialization strategy:

| Surface | Target | Manager policy |
| --- | --- | --- |
| Core value types | `QgsRectangle`, CRS values, geometries, fields, expressions, colors, enums | Copy across JSON or a documented binary codec. Highest automation potential. |
| Core object API | Projects, vector/raster/mesh layers, providers, feature sources, render settings | Generatable object IDs plus explicit lifecycle and batched operations. |
| Analysis/processing | Algorithms, feedback, task results, model inputs | Capability modules with progress/cancellation events and artifact paths. |
| Rendering/layout | Map settings, render jobs, symbols, layouts, reports | Owner-thread operations; large outputs are files or bounded pages. |
| GUI API | `QWidget`, map canvas, `QgisInterface`, actions, docks, Qt signals | Separate host-attached GUI adapter. Not part of the headless manager contract. |
| Server API | Server request/response and services | Separate server host mode; do not pretend it is a normal object registry. |
| 3D | 3D scene and Qt/OpenGL objects | Optional GUI/rendering module with its own environment and event-loop gates. |
| Providers/plugins | Provider-specific and third-party classes | Versioned capability extensions, never an unqualified promise of universal support. |
| Private/internal API | Private headers, ABI internals, undocumented classes | Excluded from the compatibility promise. |

The public QGIS C++ documentation itself is versioned: classes and members carry `Since` and deprecation information, and GUI objects such as `QgisInterface` have a different host lifecycle from core objects. Use that versioned surface to define a support matrix, not a single permanent “all” flag. See the official [QGIS repository](https://github.com/qgis/QGIS), [Qgis class reference](https://api.qgis.org/api/classQgis.html), [QgisInterface class reference](https://api.qgis.org/api/classQgisInterface.html), and [QgsProject class reference](https://api.qgis.org/api/classQgsProject.html).

## Manager shape

### Process and thread model

The manager has one owner thread. In standalone mode, the first manager start creates the owner and initializes the manager's `QgsApplication` there. Every request from another caller is copied into a queue as UTF-8 bytes; no QGIS object, Qt object, pointer, or registry entry crosses the queue.

```text
foreign caller(s)
     │ copied request bytes
     ▼
C ABI: qgis_invoke / qgis_free / qgis_transport_version
     │
     ▼
ManagerHost ── lifecycle state + request queue
     │
     ▼
QGIS owner thread
     ├── QgsApplication
     ├── OperationContext
     ├── ObjectRegistry
     └── generated operation handlers
     │
     ▼
copied JSON response buffer
```

States are explicit:

```text
cold -> starting -> ready -> stopping -> stopped
              \-> failed
```

Only `app_init` is legal before `ready`. Shutdown rejects new work, drains or fails queued work according to policy, releases registry entries on the owner thread, calls `exitQgis`, and then joins the owner. A call made from the owner thread is dispatched directly under the current operation context or returns a structured `reentrant_call` error; it must never wait on its own queue.

The current RFC 19 C ABI stays deliberately small:

```c
char *qgis_invoke(const char *request_json) noexcept;
void qgis_free(char *response_json) noexcept;
unsigned qgis_transport_version(void) noexcept;
```

`qgis_invoke` always returns a response envelope, including malformed-request, initialization, and C++ exception failures. `qgis_free` releases only buffers returned by the manager. No QGIS pointer or Qt object crosses this boundary.

### Internal components

Recommended native-manager layout under `crates/qgis-sys`:

```text
native-manager/
├── manager.cpp                 # only QGIS-header-owning translation unit
├── manager_api.h               # C ABI declarations without QGIS includes
├── manager_internal.h          # owner/queue/operation context declarations
├── registry.h                  # generational IDs and type-erased entries
├── protocol_json.h             # QJsonDocument envelope helpers
├── codecs.h                    # generated and hand-written value codecs
├── generated/
│   ├── api_manifest.json       # checked-in support inventory
│   ├── operation_table.inc     # generated dispatch registrations
│   ├── codecs.inc              # generated type codecs
│   └── api_docs.md             # generated coverage/API report
└── overrides/
    ├── ownership.yaml          # exceptional transfer/invalidation rules
    ├── types.yaml              # manual type mappings
    └── operations.yaml         # methods requiring hand-written adapters
```

D12/TASK-25.1 currently require one native manager translation unit that owns QGIS includes. Keep that rule initially: generated handler fragments are included by `manager.cpp` and do not become independent translation units with their own QGIS include policy. If compile time later demands multiple implementation units, preserve a single public include boundary and make the change an explicit build decision.

The manager should have these internal layers:

- **`ManagerHost`:** process state, owner thread, queue, startup/shutdown.
- **`RequestDecoder`:** UTF-8, JSON document, transport version, envelope and operation validation.
- **`OperationRegistry`:** generated operation name, version range, argument/result schema, owner-thread requirement, handler.
- **`OperationContext`:** request ID, cancellation/deadline, temporary IDs, error accumulator, artifact policy.
- **`ObjectRegistry`:** generational IDs, type tags, ownership policy, invalidation hooks, destruction.
- **`CodecRegistry`:** JSON/value/binary conversion for supported QGIS and Qt types.
- **`ArtifactStore`:** validated local paths, atomic writes, format/byte metadata.
- **`ErrorTranslator`:** JSON parse errors, invalid IDs, QGIS errors, exceptions, cancellation, and unsupported features.
- **`EventQueue`:** a later extension for progress/signals; the initial manager stays request/response only.

### Object registry

Use a generational ID, not a raw integer that can silently refer to a new object after reuse:

```text
ObjectId = { slot: u32, generation: u32 }
wire form = "42:7" or { "slot": 42, "generation": 7 }
```

Each entry contains:

```text
TypeTag          generated stable type identifier
Generation       stale-ID protection
Ownership        manager_owned | qgis_owned | borrowed_snapshot | singleton
Storage          type-erased pointer with a type-specific deleter
Invalidation     QObject destruction hook, project/layer signal, or owner rule
Capabilities     allowed operations for this object type
```

Ownership rules must be generated or explicitly overridden:

- **Manager-owned:** manager creates and destroys the object with its known deleter.
- **QGIS-owned:** manager stores a weak/non-owning reference and invalidates the ID when QGIS destroys the object. Never delete it from the manager.
- **Borrowed snapshot:** do not store a pointer; copy the value into the response or create a manager-owned value object.
- **Singleton:** expose a scoped manager reference to `QgsProject`, registries, or application services, with explicit invalidation at shutdown.
- **Transferred:** model transfer as an operation that changes the registry entry's ownership policy. Do not infer ownership from a pointer type.

A lookup always checks both type tag and generation. Errors are structured `invalid_object_id`, `wrong_object_type`, or `object_expired`; no invalid pointer reaches a QGIS call.

### Operation model

Use explicit stable operations for core workflows:

```json
{
  "transport_version": 1,
  "operation": "layer_open",
  "payload": {
    "uri": "points.gpkg",
    "provider": "ogr",
    "name": "points"
  }
}
```

For the long tail, generate operation names from a qualified class/member identity:

```json
{
  "transport_version": 1,
  "operation": "api_call",
  "payload": {
    "object_id": { "slot": 42, "generation": 7 },
    "type": "QgsVectorLayer",
    "method": "name",
    "arguments": []
  }
}
```

`api_call` must still resolve through generated handlers and codecs. It must not use C++ string reflection or accept arbitrary source code. The generated handler knows the overload, ownership, argument conversions, QGIS version, and result codec. For high-value workflows, expose a named operation such as `layer_open` or `render_map` instead of forcing every caller through a generic method call.

`api.describe`/`engine.info` should return:

- transport version;
- QGIS version and build/runtime capabilities;
- supported module and provider capabilities;
- type/method manifest version;
- operation names, version ranges, and required feature flags;
- excluded or partial operations only in a developer-facing coverage report, not as silently accepted calls.

## Supporting the complete API

### The generation pipeline

Do not parse headers with regular expressions. Build a version-pinned extractor:

```text
QGIS source/install
  ├── public C++ headers + include graph
  ├── SIP/binding input and ownership annotations
  ├── Doxygen/version/deprecation metadata
  └── provider/module inventory
          │
          ▼
clang AST extractor + metadata reader
          │
          ▼
normalized API model
  ├── classes, methods, overloads, enums, flags
  ├── argument/result type graph
  ├── ownership and invalidation policy
  ├── QGIS/Qt module and version range
  └── unsupported reason / manual override
          │
          ├── api_manifest.json
          ├── C++ codecs and operation handlers
          ├── qgis-protocol types/schema
          ├── Python/TypeScript ergonomic metadata
          ├── API coverage report
          └── compile/runtime contract tests
```

Use QGIS's existing binding metadata as semantic input where possible. Header ASTs tell the generator what exists; binding metadata and manual overrides tell it how ownership, factories, transfers, output arguments, and Python-visible behavior work. The manager should not invent a second incomplete ownership annotation system.

Every generated declaration receives one of these statuses:

```text
supported          generated codec + handler + test
supported_manual   hand-written adapter + test + rationale
partial            selected members only; manifest says why
unsupported        listed with reason; no runtime operation
host_only          GUI/event-loop host adapter, not headless manager
provider_optional  available only when provider/module is present
deprecated         callable only under an explicitly supported version range
```

The generator must fail the build when a newly discovered public declaration is silently dropped. It may accept an explicit `unsupported` or `host_only` entry with a reason and owner review.

### Type mapping

Start with a closed, versioned wire type system. Do not expose arbitrary `QVariant` as an untyped JSON value everywhere.

| C++/Qt type family | Wire representation | Rule |
| --- | --- | --- |
| `bool`, integral, floating | JSON boolean/number | Reject NaN/infinity unless an operation explicitly defines a representation. |
| `QString`, `QStringList`, `QByteArray` | UTF-8 string, array, or base64/temporary file | Make binary versus text explicit. |
| `QDateTime`, `QDate`, `QTime` | RFC3339/string with timezone policy | Canonical serialization and round-trip tests. |
| `QPointF`, `QRectF`, `QgsRectangle` | named JSON object | Never rely on positional arrays for public contracts. |
| enums and `QFlags` | stable string or array of strings | Keep numeric values internal; preserve unknown-value errors. |
| `QList`, `QVector`, maps | arrays/objects | Add paging or bounded limits for large results. |
| `QVariant` | tagged union | Permit only the supported variant set; return `unsupported_type` otherwise. |
| `QgsGeometry`, `QgsFeature` | WKB/GeoJSON or typed feature object | Use bounded pages and explicit CRS/field metadata. |
| `QObject*`, QGIS object pointers | generational object ID | Never serialize addresses or borrow across requests. |
| iterators and generators | page/cursor object | Cursor has owner, expiry, page size, and close semantics. |
| `QImage`, render/export output | validated path plus metadata | Follow D12's artifact policy; avoid base64 for large output. |
| signals/callbacks | event subscription ID and poll/stream record | Add only after synchronous operations are stable. |
| templates, function pointers, private classes | unsupported/manual adapter | Do not pretend these are generic JSON methods. |

### Coverage modules and sequencing

Implement coverage in vertical slices, not by generating thousands of untested methods:

1. **Runtime:** application initialization, provider registry, version/capability discovery, error and object lifecycle.
2. **Core data:** project, vector layer, fields/features, geometry, CRS, expressions, spatial indexes.
3. **Raster/mesh:** provider metadata, raster blocks, mesh datasets, bounded data extraction.
4. **Analysis/processing:** algorithm discovery, parameter models, feedback/progress, cancellation, results.
5. **Rendering/layout:** map settings, symbols, labeling, render jobs, layout/export artifacts.
6. **Server:** separate server request context and service adapters.
7. **GUI:** a separate host-attached adapter for Qt widgets, `QgisInterface`, map canvas, actions, and signals.
8. **Long tail/providers/3D:** optional generated modules with explicit environment and version capabilities.

A module is complete for a QGIS version only when its manifest, generated code, exclusions, compile checks, runtime smoke tests, and cross-language golden vectors are all present.

## GUI and plugin boundary

Do not put all of `QgisInterface` and Qt Widgets into the headless manager. A `QWidget` has GUI-thread affinity, event-loop behavior, parent ownership, and often an existing QGIS desktop owner. The manager's standalone `QgsApplication` is not a safe replacement for `iface`.

Use a separate host mode:

```text
QGIS Desktop / plugin host
  ├── owns QApplication and QgsApplication
  ├── owns iface, docks, canvases, widgets
  └── qgis-gui adapter
        ├── executes registered UI operations on the host thread
        ├── returns snapshot/value data or widget IDs scoped to the host
        └── emits events through an explicit subscription boundary

standalone headless manager
  ├── owns its QgsApplication
  ├── supports core/data/render/server modules
  └── rejects host_only operations with a structured error
```

The UI design-loop prototype can supply screenshots for this host adapter, but it must not cause a model to mutate QGIS objects or executable plugin code. Visual specs, widget layout values, and styles are the allowed model output; behavior remains under ordinary tests.

## Verification gates

The API generator and manager need more than “it compiles”:

1. **Manifest completeness:** compare extracted declarations to the checked-in manifest; every omission has an explicit reason.
2. **Generated compile gate:** compile all supported handlers against the exact QGIS/Qt version in the environment.
3. **Protocol conformance:** use the same JSON fixtures in C++, Rust, Python, and TypeScript. Check exact error kinds, field names, optional fields, and version negotiation.
4. **Ownership tests:** create, transfer, expire, close, and destroy every registry ownership category. Run under sanitizers where the QGIS build permits it.
5. **Runtime smoke tests:** one representative operation per module, headless and serialized. Keep large feature/raster results bounded.
6. **Fuzz/property tests:** malformed JSON, unknown operations, stale IDs, wrong type tags, enum values, paging limits, path traversal, and cancellation. Never fuzz uncontrolled live QGIS state.
7. **Version matrix:** build/test against each supported QGIS minor line. Record `Since`, deprecated, and provider-availability constraints in the manifest.
8. **API diff:** a QGIS upgrade produces a report of added, removed, changed, and newly unsupported declarations before code generation is accepted.
9. **Crash boundary:** C++ exceptions become error envelopes; assert that no C++ exception crosses the ABI. Do not claim in-process recovery from segmentation faults.

## Recommended first implementation

The next implementation slice should remain small:

```text
app_init
engine_info / api_describe
layer_open
layer_info
layer_close
layer_features(page)
```

It proves application lifecycle, queue ownership, generational IDs, QGIS error extraction, batched output, protocol compatibility, and shutdown without requiring a full reflection system. After that, add the extractor/manifest for the core data module before adding more hand-written operations.

## Non-goals

- A universal C++ ABI stable across QGIS major versions.
- A raw pointer or C++ object proxy exposed to Rust, Python, or Node.
- A string-based evaluator that executes arbitrary C++/Python/Qt code.
- A promise that private QGIS classes, all third-party providers, GUI objects, and every template overload are portable through the headless manager.
- Replacing QGIS's own SIP/PyQGIS surface for plugin authors who need the complete desktop API.
- Crash recovery from an in-process QGIS segmentation fault. Use a later subprocess transport for that guarantee.
