---
id: doc-5
title: QGIS SDK Testing Utilities and Cross-Language Bridge Contracts
type: specification
created_date: '2026-10-03 09:30'
---

# QGIS SDK testing utilities and cross-language bridge contracts

## Purpose

Define the testing utility architecture for the Python QGIS SDK and the TypeScript/JavaScript bridge. The utilities must test the public behavior of plugins and bridge clients without attempting to simulate the entire QGIS application.

This document is the detailed execution design for the testing migration anchored by TASK-23. It also aligns the bridge test seam with the engine-plus-wire architecture: Python and TypeScript use protocol-faithful test transports, while Qt/QGIS integration remains a separate environment-gated layer.

## Design goals

The utilities must provide:

1. isolated fixtures by default;
2. protocol-faithful fake transports;
3. deterministic network, task, event, and clock behavior;
4. pure-Python tests without QGIS or Qt;
5. optional Qt and real-QGIS fixtures;
6. shared bridge contract fixtures and golden values;
7. property-based strategies for pure values and protocol invariants;
8. compatibility exports so existing tests do not break.

They must not attempt to build a fake QGIS application or hide a failed QGIS/Qt precondition by silently switching to a fake.

## Testing layers

```text
pure unit tests
  no Qt, no QGIS, no WebEngine
  specs, validation, protocol, policy, serialization

host fakes
  deterministic FakeIface, FakeDialog, FakeTransport, FakeTaskManager
  plugin behavior through public seams

Qt tests
  QApplication, QT_QPA_PLATFORM=offscreen
  native widget construction and lifecycle

QGIS tests
  QgsApplication/QGIS providers, serialized execution
  real layers, projects, processing, task manager

WebEngine tests
  isolated optional environment
  QWebEngine/QWebChannel startup and browser-facing behavior

cross-language contract tests
  same bridge manifests, requests, responses, errors, and events
  consumed by Python and TypeScript suites
```

A pure test must not initialize QGIS. A QGIS test must not silently pass using a fake. A WebEngine test must be isolated from ordinary Qt tests because startup and headless behavior differ.

## Python utility architecture

The current `qgis_sdk.testing` module contains fakes, factories, pytest plugin registration, environment detection, network behavior, task behavior, UI behavior, and bridge behavior. Split it behind the existing compatibility facade:

```text
qgis_sdk/testing/
├── __init__.py          # compatibility exports
├── environment.py       # pure, Qt, QGIS, WebEngine detection
├── calls.py             # Call and CallLog
├── iface.py             # FakeIface, FakeAction, message bar
├── ui.py                # FakeDialog, FakeWidget, FakeWebView
├── bridge.py            # FakeBridgeEndpoint, BridgeHarness
├── network.py           # FakeTransport, FakeResponse, request history
├── tasks.py             # deterministic task manager/state machine
├── processing.py        # FakeContext, FakeSource, FakeSink
├── data.py              # feature, geometry, field builders
├── strategies.py        # Hypothesis strategies
└── plugin.py            # pytest fixtures and markers
```

Existing imports such as `from qgis_sdk.testing import FakeIface` and fixture names such as `fake_iface` remain valid while implementation moves behind the facade.

### Shared call recorder

All fakes should record calls through one shape:

```python
@dataclass(frozen=True)
class Call:
    target: str
    method: str
    args: dict[str, Any]
```

The recorder must support:

```python
calls.all()
calls.for_method("layers.add_vector")
calls.assert_called_once(...)
calls.reset()
```

Do not maintain unrelated request-log formats for network, tasks, bridge, and interface fakes.

### Python bridge harness

The bridge fake must exercise the protocol rather than directly invoking arbitrary fake methods:

```python
bridge = BridgeHarness(
    descriptions={
        "bridge": bridge_description,
        "qgis": qgis_description,
    },
    handlers={
        ("qgis", "layers.list"): lambda args: [...],
        ("qgis", "layers.add_vector"): lambda args: {...},
    },
)

response = bridge.invoke({
    "bridge_version": 1,
    "request_id": "req-1",
    "target": "qgis",
    "method": "layers.list",
    "args": {},
})
```

The harness tests request validation, request-ID correlation, method lookup, argument validation, result serialization, structured errors, permissions, event emission, task progress, and unknown target/method behavior.

### Network fake

Use a scripted transport instead of a fake copy of every network backend:

```python
transport = FakeNetworkTransport()
transport.reply(
    "GET",
    "https://example.test/layers",
    FakeResponse(status_code=200, json_data={"layers": []}),
)
```

It should support `reply`, `fail`, `delay`, `redirect`, `reply_sequence`, `calls`, and reset. Test transport behavior separately from response normalization, retry policy, session/decorator behavior, and content fetching.

### Deterministic task fake

Model task states explicitly:

```text
PENDING -> RUNNING -> SUCCESS
                    -> FAILURE
                    -> CANCELED
```

The fake manager should support both automatic and manual execution:

```python
manager = FakeTaskManager(auto_run=False)
result = manager.submit(work)
assert result.state == "PENDING"
manager.run_next()
assert result.state == "SUCCESS"
```

Test progress, cancellation, callbacks, ordering, failure, chains, groups, and result methods without sleeping or starting real worker threads.

### Python environment fixtures

Provide these explicit fixture/marker pairs:

```python
pure_python
qt_app
qgis_app
webengine_app
```

Markers:

```python
@pytest.mark.pure_python
@pytest.mark.qt
@pytest.mark.qgis
@pytest.mark.webengine
```

Rules:

- `pure_python` has no QGIS/Qt initialization;
- `qt_app` sets `QT_QPA_PLATFORM=offscreen` before binding import;
- `qgis_app` owns one serialized QGIS lifecycle;
- WebEngine tests use their own optional environment and timeout policy;
- missing required environment produces a clear skip or prerequisite failure, never a false green result.

### Hypothesis strategies

Generate pure data only:

```text
extent_strategy
zoom_range_strategy
crs_auth_id_strategy
plugin_name_strategy
field_spec_strategy
bridge_request_strategy(description)
network_response_strategy
task_transition_strategy
```

Do not generate arbitrary live QGIS objects. Use explicit real fixtures for QGIS application, layers, providers, and project files.

Useful properties include:

- request IDs are preserved in bridge responses;
- unknown methods produce structured errors;
- valid field specs render deterministic models;
- task transitions never skip illegal states;
- retry policy stops at its configured limit;
- network chunks reconstruct the original content;
- extent and bridge description serialization round-trip.

## TypeScript utility architecture

The existing `@qgis/test-utils` package already has `createFixture`, `installBridgeGlobals`, a scripted QWebChannel, call logs, and `fast-check`. Extend it without making every test mutate browser globals.

```text
@qgis/test-utils
├── fixture.ts
├── bridge-harness.ts
├── scripted-transport.ts
├── contract-fixtures.ts
├── fake-clock.ts
├── assertions.ts
├── arbitraries.ts
└── index.ts
```

### `BridgeHarness`

```typescript
const harness = createBridgeHarness({
  descriptions: {
    bridge: bridgeDescription,
    qgis: qgisDescription,
  },
  handlers: {
    "qgis.layers.list": () => [
      { id: "layer-1", name: "Roads" },
    ],
    "qgis.message.info": () => true,
  },
});
```

Expose:

```typescript
harness.calls
harness.reply(target, method, value)
harness.reject(target, method, error)
harness.emit(event, data)
harness.reset()
harness.restore()
```

Feature tests should inject `harness.transport` into the bridge client. `installBridgeGlobals` remains available for testing QWebChannel discovery, description loading, and global restoration.

### TypeScript assertions

Provide helpers such as:

```typescript
expectBridgeCall(harness, {
  target: "qgis",
  method: "layers.add_vector",
  args: {
    uri: "/data/roads.gpkg",
    name: "Roads",
  },
});
```

And:

```typescript
await expectBridgeError(
  () => qgis.layers.addVector(...),
  "invalid_arguments",
);
```

Tests should observe the public client and transport calls, not `_rawBridge` internals.

### Fast-check properties

Add properties for:

- request/response correlation by request ID;
- callback and Promise result equivalence;
- JSON string and decoded-object normalization;
- malformed JSON producing one structured error;
- every described method creating one callable proxy;
- unknown methods failing predictably;
- fixture installation/restoration preserving previous globals;
- event subscribe/emit/unsubscribe behavior;
- task progress retaining task ID and monotonic progress.

## Shared cross-language contract fixtures

Create one language-neutral fixture area:

```text
test-fixtures/
└── bridge/
    ├── descriptions/
    │   ├── bridge.json
    │   └── qgis.json
    ├── requests/
    │   ├── layers-list.json
    │   └── layers-add-vector.json
    ├── responses/
    │   ├── success.json
    │   └── invalid-arguments.json
    └── events/
        └── task-progress.json
```

The manifest should describe methods, arguments, results, permissions, and events:

```json
{
  "name": "qgis",
  "version": "1.0",
  "methods": [
    {
      "name": "layers.list",
      "args": {},
      "result": "LayerInfo[]",
      "permissions": ["layer.read"]
    }
  ],
  "events": [
    {
      "name": "task.progress",
      "payload": "TaskProgress"
    }
  ]
}
```

Python uses the fixtures to validate router dispatch and serialization. TypeScript uses them to validate proxy creation and client behavior. Both languages retain explicit golden examples for known interoperability values.

Shared fixtures include:

```text
request envelopes
response envelopes
error kinds
bridge descriptions
event payloads
known QGIS values
```

Do not force both languages to share fake implementation classes. Share the observable contract.

## Bridge test layers

The bridge should be tested at four seams:

1. **Python router:** request JSON to handler/result JSON.
2. **QWebChannel endpoint:** one endpoint, callback behavior, lifecycle, event emission.
3. **TypeScript transport:** QWebChannel callback to Promise/error normalization.
4. **Typed feature facades:** `qgis.layers`, `qgis.tasks`, `qgis.message`, and other APIs call the expected target/method.

The high-level facade tests should use a scripted transport. Only loader/global tests should install `window`, `qt`, `QWebChannel`, and injected descriptions.

## Isolation rules

- Default fixture scope is one test.
- File/session scope is permitted only for immutable descriptions or the Qt application singleton.
- Every global fixture has an explicit restore function.
- No test relies on execution order.
- No test uses real network access.
- No test sleeps to wait for fake tasks.
- QGIS/Qt tests run serialized.
- WebEngine tests are optional and separate from pure bridge tests.
- Fakes expose only the behavior consumed by production code; they are not general QGIS reimplementations.

## Implementation sequence

1. Define bridge request/response/event schemas and error kinds.
2. Add Python `BridgeRouter` and `BridgeHarness`.
3. Add TypeScript `BridgeTransport` and `BridgeHarness`.
4. Convert one API, preferably `message.info`, to the new transport seam.
5. Convert `layers`, `project`, and `tasks`.
6. Centralize TypeScript callback normalization, JSON decoding, errors, timeouts, and fallback behavior.
7. Add shared contract fixtures consumed by Python and TypeScript.
8. Add Hypothesis and fast-check properties.
9. Split `qgis_sdk.testing` behind compatibility exports.
10. Move Qt/QGIS/WebEngine tests into explicit environment groups.
11. Remove duplicated raw callback/JSON logic after one full compatibility gate.

## Verification gates

A slice is complete only when:

- pure Python tests pass without QGIS/Qt;
- TypeScript tests pass using the scripted transport;
- shared fixture vectors pass in both languages;
- no global fixture leaks into the following test;
- QGIS/Qt tests pass in the restored Pixi environment with offscreen/serialized settings;
- behavior tests still cover public plugin seams;
- property tests have bounded, useful shrinking;
- known cross-language golden values remain unchanged.

## Non-goals

- A fake implementation of all QGIS classes.
- Replacing real QGIS integration tests with mocks.
- Requiring QWebEngine for ordinary bridge tests.
- Making implementation details such as `_rawBridge` part of the test contract.
- Removing explicit examples and golden values in favor of properties alone.
