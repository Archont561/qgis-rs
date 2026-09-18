# Refactor Plan — Split packages-py / packages-node, declarative decorator API, windows-like bridge

**Date:** 2026-09-18
**Branch:** `arena/01a0b44f-qgis-rs`
**Goal:** Make repo maintainable, language-separated, declarative, testable, with bridge that feels like native browser APIs (EventSource/WebSocket/window).

---

## 0. Current State Pain Points

- `packages/qgis-sdk` mixes Python + Rust (`src/` Python, `src_rs/` Rust bins) — confusing for maturin + npm.
- `packages/qgis-sdk-bridge` is JS-only but lives next to Python, and its `src/` contains stray Python files (copy-paste bug: `__init__.py`, `bridge.py` etc inside bridge package).
- `packages/qgis-node` and `packages/qgis-rs` are Rust workspaces with JS/Python wrappers but not aligned.
- `tests/` is flat (`test_network.py`, `test_tasks.py`) not mirroring `src/qgis_sdk/` structure → hard to find, no per-module coverage.
- Bridge today: Python class → codegen `bridge.d.ts` + `bridge.js` package. User must run `qgis-plugin bridge generate` after every change. No runtime loading of description. JS API is callback-based with Promise wrapper, not windows-like.
- Plugin API: class-based `Plugin` with `@toolbar/@action` but still imperative `init_gui`. Want mostly decorators, like FastAPI / Celery / click.

---

## 1. Proposed New Layout

```
/
├── packages-py/
│   ├── qgis-sdk/                 # Python SDK (pure-py + optional Rust _core)
│   │   ├── src/qgis_sdk/
│   │   │   ├── __init__.py
│   │   │   ├── plugin/
│   │   │   │   ├── __init__.py   # declarative decorators
│   │   │   │   ├── decorators.py # @plugin, @toolbar, @action, @menu, @task, @bridge
│   │   │   │   ├── base.py       # PluginBase, ActionSpec
│   │   │   │   └── registry.py   # global registry for decorators
│   │   │   ├── network/
│   │   │   │   ├── __init__.py   # requests-like API, Session, Response
│   │   │   │   ├── manager.py    # NetworkManager (QgsNAM wrapper)
│   │   │   │   ├── session.py    # Session
│   │   │   │   └── fetcher.py    # ContentFetcher
│   │   │   ├── tasks/
│   │   │   │   ├── __init__.py   # celery-like API
│   │   │   │   ├── manager.py    # TaskManager
│   │   │   │   ├── task.py       # Task, TaskWrapper, AsyncResult
│   │   │   │   └── signature.py  # Signature, Chain, group
│   │   │   ├── bridge/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── description.py # BridgeDescription, MethodDescription (no codegen)
│   │   │   │   ├── decorators.py  # @bridge, @method, @slot, @signal
│   │   │   │   ├── runtime.py    # BridgeRuntime — loads description, registers QWebChannel
│   │   │   │   ├── window.py     # Window-like object (EventSource/WebSocket API)
│   │   │   │   └── loader.py     # load_bridge_description()
│   │   │   ├── ui/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dialog.py
│   │   │   │   ├── webview.py
│   │   │   │   └── decorators.py # @dialog, @web_dialog
│   │   │   ├── algorithm/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   └── decorators.py # @alg, @param, @output
│   │   │   ├── testing/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── iface.py
│   │   │   │   ├── network.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── web.py
│   │   │   │   └── fixtures.py   # pytest fixtures
│   │   │   ├── scaffold/
│   │   │   │   ├── __init__.py
│   │   │   │   └── templates/
│   │   │   └── cli/
│   │   │       ├── __init__.py
│   │   │       └── commands/
│   │   ├── tests/
│   │   │   ├── qgis_sdk/
│   │   │   │   ├── plugin/
│   │   │   │   │   ├── test_decorators.py
│   │   │   │   │   └── test_registry.py
│   │   │   │   ├── network/
│   │   │   │   │   ├── test_manager.py
│   │   │   │   │   ├── test_session.py
│   │   │   │   │   └── test_response.py
│   │   │   │   ├── tasks/
│   │   │   │   │   ├── test_task.py
│   │   │   │   │   ├── test_manager.py
│   │   │   │   │   └── test_celery_api.py
│   │   │   │   ├── bridge/
│   │   │   │   │   ├── test_description.py
│   │   │   │   │   ├── test_runtime.py
│   │   │   │   │   └── test_window.py
│   │   │   │   ├── ui/
│   │   │   │   │   └── test_dialog.py
│   │   │   │   └── testing/
│   │   │   │       ├── test_iface.py
│   │   │   │       └── test_fakes.py
│   │   │   └── conftest.py
│   │   ├── pyproject.toml
│   │   └── Cargo.toml (for _core)
│   │
│   ├── qgis-bridge/              # Python bridge description package (no codegen)
│   │   ├── src/qgis_bridge/
│   │   │   ├── __init__.py
│   │   │   ├── description.py
│   │   │   ├── window.py
│   │   │   └── runtime.py
│   │   ├── tests/qgis_bridge/
│   │   │   ├── test_description.py
│   │   │   └── test_window.py
│   │   └── pyproject.toml
│   │
│   └── qgis-rs-py/               # Python wrapper for qgis-rs (render)
│       ├── src/qgis_rs/
│       └── tests/qgis_rs/
│
├── packages-node/
│   ├── qgis-sdk-bridge/          # @qgis-sdk/bridge — JS/TS bridge, windows-like
│   │   ├── src/
│   │   │   ├── index.ts          # createBridge, Bridge as EventTarget
│   │   │   ├── window.ts         # BridgeWindow extends EventTarget (EventSource-like)
│   │   │   ├── loader.ts
│   │   │   ├── react.ts
│   │   │   ├── vue.ts
│   │   │   ├── webcomponents.ts
│   │   │   └── description.ts    # loads BridgeDescription JSON from Python
│   │   ├── tests/
│   │   │   ├── bridge/
│   │   │   │   ├── test_window.test.ts
│   │   │   │   ├── test_description.test.ts
│   │   │   │   └── test_loader.test.ts
│   │   │   └── package.json
│   │
│   ├── qgis-sdk-cli/             # node wrapper for qgis-plugin binary
│   │   ├── src/
│   │   └── package.json
│   │
│   └── qgis-rs-node/             # JS wrapper for qgis-rs
│       ├── src/
│       └── tests/
│
├── packages-rs/
│   ├── qgis-sdk-core/            # Rust core for qgis-sdk (metadata, scaffold)
│   │   └── src/
│   ├── qgis-rs-core/
│   └── qgis-cli-core/
│
└── apps/
    └── docs/
```

**Migration steps:**
1. `mkdir -p packages-py packages-node packages-rs`
2. `git mv packages/qgis-sdk packages-py/qgis-sdk`
3. `git mv packages/qgis-sdk-bridge packages-node/qgis-sdk-bridge` (and clean stray py files)
4. `git mv packages/qgis-node packages-node/qgis-rs-node` etc.
5. Update root `Cargo.toml` workspace members.
6. Update `pyproject.toml` `tool.maturin.manifest-path` to `../../packages-rs/qgis-sdk-core/Cargo.toml` or keep per-package Cargo.
7. Update CI to test `packages-py/*` with `pytest` and `packages-node/*` with `npm test`.

---

## 2. Bridge Package — Python Description Loader, not Codegen

### Problem today
- User defines `class Bridge: def get_layer(self) -> dict: ...`
- Must run `qgis-plugin bridge generate --bridge ... --output web/bridge.d.ts` → generates TS file.
- If method changes, TS out of sync.
- Generated package includes `bridge.js` etc — heavy.

### Desired: description + runtime loader

**Python side — declarative description, no codegen:**

```python
# qgis_sdk/bridge/description.py
from dataclasses import dataclass
from typing import List, Literal

@dataclass
class MethodDescription:
    name: str
    args: List[str]
    arg_types: List[str]  # py types as string
    return_type: str
    doc: str = ""
    is_signal: bool = False
    is_slot: bool = True

@dataclass
class BridgeDescription:
    name: str
    methods: List[MethodDescription]
    signals: List[MethodDescription] = None
    version: str = "1.0"

    def to_json(self): ...
    @classmethod
    def from_class(cls, py_cls): ...  # introspects class
    @classmethod
    def from_json(cls, data): ...
```

```python
# qgis_sdk/bridge/decorators.py
from .description import BridgeDescription, MethodDescription
from .registry import bridge_registry

def bridge(name="bridge", description=None):
    def decorator(cls):
        desc = BridgeDescription.from_class(cls, name=name)
        bridge_registry.register(desc, cls)
        cls._bridge_description = desc
        return cls
    return decorator

def method(return_type=None, doc=None):
    def decorator(func):
        func._is_bridge_method = True
        func._return_type = return_type
        return func
    return decorator

def signal(arg_types=None):
    def decorator(func):
        func._is_signal = True
        return func
    return decorator

# Usage
@bridge(name="my_bridge")
class MyBridge:
    @method(return_type=dict, doc="Get layer")
    def get_layer(self, layer_id: str) -> dict:
        return {"name": layer_id}

    @signal()
    def layer_changed(self, layer_id: str):
        pass
```

**Runtime — loads description, no codegen needed:**

```python
# qgis_sdk/bridge/runtime.py
class BridgeRuntime:
    def __init__(self, description: BridgeDescription, impl_instance):
        self.description = description
        self.impl = impl_instance
        self._channel = None
        self._window = None

    def register(self, webview):
        # Creates QWebChannel, registers impl
        # Also injects description as JSON for JS to load
        channel = QWebChannel()
        channel.registerObject(self.description.name, self.impl)
        webview.page().setWebChannel(channel)
        # Inject description JSON into window
        json_str = self.description.to_json()
        webview.page().runJavaScript(f"window.__QGIS_BRIDGE_DESCRIPTION__ = {json_str}")

    def to_window(self):
        # Returns window-like object for Python → JS
        return BridgeWindow(self)

class BridgeWindow:
    # EventSource/WebSocket-like for Python side too
    def __init__(self, runtime):
        self.runtime = runtime
        self._listeners = {}

    def add_event_listener(self, event, callback):
        self._listeners.setdefault(event, []).append(callback)

    def dispatch_event(self, event, data):
        # Calls JS via runJavaScript
        self.runtime.webview.page().runJavaScript(
            f"window.qgisBridge.dispatchEvent(new CustomEvent('{event}', {{detail: {json.dumps(data)}}}))"
        )

    def send(self, data):
        self.dispatch_event("message", data)
```

**JS side — loads description JSON, no codegen:**

```typescript
// packages-node/qgis-sdk-bridge/src/description.ts
export interface MethodDescription { name: string; args: string[]; return_type: string; }
export interface BridgeDescription { name: string; methods: MethodDescription[]; version: string; }

export function loadDescription(): BridgeDescription | null {
  return (window as any).__QGIS_BRIDGE_DESCRIPTION__ || null;
}

export function createBridgeFromDescription<T>(desc: BridgeDescription): T {
  // Dynamically creates methods based on description
  const raw = {} as any;
  desc.methods.forEach(m => {
    raw[m.name] = (...args: any[]) => {
      // Will be replaced by QWebChannel promisify
      return new Promise((resolve, reject) => {
        // QWebChannel will inject actual impl
      });
    };
  });
  return raw as T;
}
```

User can still codegen if wants, but default is runtime.

**CLI change:**
- `qgis-plugin bridge describe --bridge my_plugin:MyBridge --output web/bridge.json` → outputs JSON description, not TS.
- `qgis-plugin bridge generate` becomes optional, for TS types if user wants static typing.
- JS can work without any generated file: `const bridge = await createBridge()` loads description from `window.__QGIS_BRIDGE_DESCRIPTION__`.

---

## 3. Bridge as Windows-like Object (EventSource / WebSocket API)

### Desired API

Look at `EventSource` and `WebSocket` and `window`:

- `EventSource`: `addEventListener`, `onmessage`, `onopen`, `onerror`, `close()`, `readyState`
- `WebSocket`: `send()`, `close()`, `addEventListener('message'/'open'/'close'/'error')`, `readyState`, `url`
- `window`: `addEventListener`, `dispatchEvent`, `postMessage`

**Proposed JS BridgeWindow:**

```typescript
// packages-node/qgis-sdk-bridge/src/window.ts
export class QgisBridge extends EventTarget {
  // Like WebSocket + EventSource
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState: number = QgisBridge.CONNECTING;
  url: string = "qgis://bridge";
  description: BridgeDescription | null = null;

  // Properties like window
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;

  // Bridge methods dynamically added
  [method: string]: any;

  constructor(objectName = "bridge", options: BridgeOptions = {}) {
    super();
    this._objectName = objectName;
    this._options = options;
  }

  // WebSocket-like
  send(data: any) {
    // Calls Python method if exists, or dispatches to Python via custom method
    if (this._rawBridge && this._rawBridge.send) {
      return this._rawBridge.send(data);
    }
    this.dispatchEvent(new MessageEvent("message", { data }));
  }

  close(code?: number, reason?: string) {
    this.readyState = QgisBridge.CLOSED;
    this.dispatchEvent(new CloseEvent("close", { code, reason }));
  }

  // EventSource-like
  addEventListener(type: string, listener: EventListener, options?: any) {
    super.addEventListener(type, listener, options);
  }

  removeEventListener(type: string, listener: EventListener) {
    super.removeEventListener(type, listener);
  }

  // Window-like
  postMessage(message: any, targetOrigin?: string) {
    this.dispatchEvent(new MessageEvent("message", { data: message }));
  }

  // Bridge method call — like window.fetch but for bridge
  async call<T>(method: string, ...args: any[]): Promise<T> {
    if (!this._rawBridge || typeof this._rawBridge[method] !== "function") {
      throw new Error(`Method ${method} not found`);
    }
    return this._rawBridge[method](...args);
  }

  // Convenience — direct method access via Proxy
  // bridge.get_layer() -> calls this.call("get_layer")
}

// Factory — like new EventSource(url) or new WebSocket(url)
export async function createBridge<T = QgisBridge>(
  objectName = "bridge",
  options: BridgeOptions = {}
): Promise<T & QgisBridge> {
  const win = new QgisBridge(objectName, options) as T & QgisBridge;
  await win._connect(); // loads qwebchannel.js, connects, loads description
  win.readyState = QgisBridge.OPEN;
  win.dispatchEvent(new Event("open"));
  return win;
}

// Usage
// Vanilla
const bridge = await createBridge();
bridge.addEventListener("open", () => console.log("open"));
bridge.addEventListener("message", (e) => console.log(e.data));
bridge.addEventListener("layer_changed", (e) => console.log("layer changed", e.detail));
bridge.onmessage = (e) => console.log(e.data);

const layer = await bridge.get_layer("my_layer"); // method from description
await bridge.call("get_layer", "my_layer");

bridge.send({action: "buffer"});

// React
const { bridge, ready } = useQgisBridge(); // returns QgisBridge
useEffect(() => {
  if (!ready) return;
  const handler = (e) => setLayer(e.detail);
  bridge.addEventListener("layer_changed", handler);
  return () => bridge.removeEventListener("layer_changed", handler);
}, [ready]);

// Vue
const { bridge, ready } = useQgisBridge();
watch(ready, (r) => {
  if (r) bridge.addEventListener("message", (e) => console.log(e.data));
});

// Web Components
// <qgis-bridge></qgis-bridge> extends QgisBridge
```

**Python side window-like too:**

```python
# qgis_sdk/bridge/window.py
class BridgeWindow(EventTarget):
    def add_event_listener(self, event, callback): ...
    def remove_event_listener(self, event, callback): ...
    def dispatch_event(self, event, data): ... # sends to JS
    def send(self, data): ...
    def close(self): ...
    def post_message(self, data): ...

# Usage
window = bridge_runtime.to_window()
window.add_event_listener("message", lambda e: print(e.data))
window.send({"action": "buffer"})
window.dispatch_event("layer_changed", {"layer_id": "test"})
```

---

## 4. Tests/ Mimic Src/ Structure

### Current
```
src/qgis_sdk/network.py
tests/test_network.py  # flat
```

### Desired
```
src/qgis_sdk/network/
  __init__.py
  manager.py
  session.py
tests/qgis_sdk/network/
  test_manager.py
  test_session.py
  test_response.py
  conftest.py  # fixtures for network
```

**Rules:**
- `tests/` mirrors `src/` package structure: `src/qgis_sdk/foo/bar.py` → `tests/qgis_sdk/foo/test_bar.py` or `tests/qgis_sdk/foo/bar/test_*.py`
- Each `src` subpackage has `tests/<package>/...` with same subdirs.
- `conftest.py` at root imports all fixtures from `qgis_sdk.testing` and per-subpackage fixtures.
- Use own fakes: `fake_session`, `fake_network_manager`, `fake_task_manager`, etc.

**Example for network:**

```
packages-py/qgis-sdk/
  src/qgis_sdk/network/
    __init__.py      # exports get, post, Session, NetworkResponse
    manager.py       # NetworkManager
    session.py       # Session
    response.py      # NetworkResponse, exceptions
    fetcher.py       # ContentFetcher
  tests/qgis_sdk/network/
    __init__.py
    test_response.py      # uses fake_network_response fixture
    test_manager.py       # uses fake_network_manager fixture
    test_session.py       # uses fake_session fixture, tests requests-like API
    test_fetcher.py       # uses fake_content_fetcher
    conftest.py           # from qgis_sdk.testing import ...
```

**Pytest config:**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

**For node:**

```
packages-node/qgis-sdk-bridge/
  src/
    window.ts
    loader.ts
    description.ts
  tests/
    bridge/
      window.test.ts      # mirrors src/window.ts
      loader.test.ts
      description.test.ts
```

Use `vitest` or `jest` with `tests/` mirroring `src/`.

---

## 5. qgis-sdk Declarative API via Decorators Mostly

### Goal: 90% decorator, minimal class boilerplate

Inspired by FastAPI, Celery, click, Flask.

**Current:**

```python
class MyPlugin(Plugin):
    name = "My Plugin"
    @toolbar("My Toolbar")
    @action(tooltip="Run")
    def run(self, iface): ...
```

**Desired — fully declarative:**

```python
from qgis_sdk import plugin, toolbar, action, task, bridge, param, setting

@plugin(
    name="My Plugin",
    version="0.1.0",
    author="Me",
    qgis_min_version="3.28",
    category="Vector"
)
class MyPlugin:
    # No need to subclass Plugin — decorator creates metadata.txt, classFactory etc

    @setting(default=0.5, persist=True)
    def threshold(self): return 0.5

    @toolbar("My Toolbar")
    @action(tooltip="Run", icon="icons/run.svg")
    def run(self, iface, threshold: float = None):
        # threshold injected from setting
        layer = iface.activeLayer()
        # Use network — requests-like
        import qgis_sdk.network as requests
        resp = requests.get("https://example.com/api", params={"q": threshold})
        resp.raise_for_status()

    @toolbar("My Toolbar")
    @action(tooltip="Fetch data")
    def fetch_data(self, iface):
        from .services.network import get_session
        session = get_session(auth_cfg="my_auth")
        resp = session.get("https://example.com/secure")
        iface.messageBar().pushMessage(f"Fetched {resp.json()}")

    @toolbar("My Toolbar")
    @action(tooltip="Run background task")
    def run_task(self, iface):
        # Celery-like
        result = self.my_task.delay(42)
        iface.messageBar().pushMessage(f"Task {result.id} started")
        # result.get() would block, so use on_finished

    @task("My background task", bind=True, can_cancel=True)
    def my_task(self, value: int = 10):
        self.set_progress(50)
        if self.is_canceled():
            return None
        return value * 2

    @bridge(name="my_bridge")
    class Bridge:
        @method(return_type=dict)
        def get_layer(self, layer_id: str) -> dict:
            return {"name": layer_id, "count": 100}

        @method()
        def log(self, msg: str) -> str:
            print(msg)
            return "ok"

        @signal()
        def layer_changed(self, layer_id: str):
            pass

    @bridge.window
    def on_bridge_message(self, window, event):
        # window is BridgeWindow — EventSource-like
        window.add_event_listener("message", lambda e: print(e.data))
        window.send({"status": "ready"})
```

**Implementation — registry:**

```python
# qgis_sdk/plugin/registry.py
class PluginRegistry:
    def __init__(self):
        self.plugins = {}
        self.actions = {}
        self.tasks = {}
        self.bridges = {}

    def register_plugin(self, cls, metadata): ...
    def register_action(self, func, toolbar, menu, tooltip): ...
    def register_task(self, func, description, bind): ...
    def register_bridge(self, cls, name): ...

registry = PluginRegistry()

def plugin(**metadata):
    def decorator(cls):
        registry.register_plugin(cls, metadata)
        # Inject classFactory, metadata_txt, init_gui from registry
        cls._qgis_sdk_metadata = metadata
        cls._qgis_sdk_registry = registry
        # Generate methods dynamically
        original_init = getattr(cls, "__init__", lambda self, iface: None)
        def __init__(self, iface):
            self.iface = iface
            self._registry = registry
            original_init(self, iface)
        cls.__init__ = __init__

        def init_gui(self):
            for action_spec in registry.get_actions(cls):
                # create QAction via iface
                pass

        cls.init_gui = init_gui
        cls.metadata_txt = lambda: render_metadata(metadata)
        return cls
    return decorator

def toolbar(name):
    def decorator(func):
        registry.register_action(func, toolbar=name)
        return func
    return decorator

def action(tooltip=None, icon=None, menu=None):
    def decorator(func):
        registry.register_action(func, tooltip=tooltip, icon=icon, menu=menu)
        return func
    return decorator

# Similarly for task, bridge, etc
def task(description="Task", bind=False, can_cancel=True):
    def decorator(func):
        wrapper = TaskWrapper(func, description, bind, can_cancel)
        registry.register_task(wrapper)
        return wrapper
    return decorator
```

**For algorithm — declarative too:**

```python
from qgis_sdk import algorithm, param, output

@algorithm(id="my_plugin:buffer", name="Buffer", group="Vector")
class BufferAlg:
    input_layer = param.source("Input layer")
    distance = param.distance("Distance", default=10.0)
    output_layer = output.sink("Buffered")

    def process(self, context, feedback, input_layer, distance):
        # params injected
        feedback.set_progress(50)
        return {self.output_layer: input_layer}
```

**For network — already declarative via Session, but add decorator for auto-auth:**

```python
from qgis_sdk.network import with_auth, session

@with_auth(auth_cfg="my_auth")
def fetch_secure(url, params=None):
    import qgis_sdk.network as requests
    return requests.get(url, params=params).json()

@session(auth_cfg="my_auth", headers={"User-Agent": "MyPlugin"})
def fetch_with_session(session, url):
    return session.get(url).json()
```

---

## 6. Self-Installing Runtime Helper — Plugin Zip That Bootstraps qgis-sdk Without pip CLI

### Problem
- QGIS plugins are distributed as **zip** via QGIS Plugin Repository, installed via QGIS Plugin Manager — not via `pip`.
- QGIS Python environment often has no `pip` on PATH, or user doesn't know CLI. Plugin author wants to publish `my_plugin.zip` and have it "just work": if `qgis-sdk` missing, it asks user to install or auto-installs.
- Current `qgis-sdk` requires `pip install qgis-sdk` beforehand — fails in vanilla QGIS.

### Desired: Plugin that registers itself and bootstraps its own core runtime

**User story:**
1. Author does `qgis-plugin new my_plugin --bundle` → generates `my_plugin.zip` that includes `extlibs/` or `vendor/qgis_sdk` or a small `bootstrap.py` + wheel.
2. User installs zip via QGIS Plugin Manager.
3. On `classFactory(iface)` first load:
   - Plugin checks if `qgis_sdk` importable.
   - If not, shows `QMessageBox`: "My Plugin requires qgis-sdk, install now? [Yes/No] [Auto-install / Manual instructions]"
   - If Yes + auto-install:
     - Tries `pip install qgis-sdk --target <plugin>/extlibs` via `subprocess` or `import pip`
     - If pip fails (no internet, no pip), tries offline wheel bundled in zip (`wheels/qgis_sdk-0.1.0-py3-none-any.whl`) → unzip via `zipfile` into `extlibs`
     - Adds `extlibs` to `sys.path`
     - Tries import again.
   - If still fails, shows manual instructions: `pip install qgis-sdk` or `conda install -c conda-forge qgis-sdk`, with link to docs.
   - Once `qgis_sdk` available, plugin registers itself declaratively and continues.

**Design — small vendored bootstrap (single file, no deps):**

```
my_plugin/
  __init__.py          # tries import qgis_sdk, falls back to bootstrap
  bootstrap.py         # < 300 LOC, pure-python, vendored from qgis_sdk, can be copied
  extlibs/             # created at runtime or at package time
    qgis_sdk/
  wheels/              # optional offline wheel for offline install
    qgis_sdk-0.1.0-py3-none-any.whl
  vendor/              # alternative: fully vendored qgis_sdk (pure-py) at build time
    qgis_sdk/
```

**`qgis_sdk/bootstrap.py` (to be vendored):**

```python
"""
qgis_sdk.bootstrap — tiny helper that can be vendored into plugin zip.
No dependencies, works without qgis_sdk installed.
Usage in plugin __init__.py:

    try:
        import qgis_sdk
    except ImportError:
        from .bootstrap import ensure_qgis_sdk
        if not ensure_qgis_sdk(auto_install=True, ask_user=True, parent=None):
            def classFactory(iface): return None
            raise

    from qgis_sdk import plugin, toolbar, action
    ...
"""

import sys
import pathlib
import subprocess
import zipfile
import urllib.request

def _get_plugin_dir():
    return pathlib.Path(__file__).parent

def _get_extlibs_dir():
    return _get_plugin_dir() / "extlibs"

def _ensure_extlibs_in_path():
    extlibs = _get_extlibs_dir()
    if str(extlibs) not in sys.path:
        sys.path.insert(0, str(extlibs))
    return extlibs

def is_qgis_sdk_installed():
    try:
        import qgis_sdk
        return True
    except ImportError:
        return False

def install_from_pip(target_dir=None, auto_confirm=False):
    target_dir = pathlib.Path(target_dir or _get_extlibs_dir())
    target_dir.mkdir(parents=True, exist_ok=True)
    # Try pip
    try:
        # Use python -m pip to avoid PATH issues
        cmd = [sys.executable, "-m", "pip", "install", "qgis-sdk", "--target", str(target_dir), "--no-deps", "--quiet"]
        if auto_confirm:
            cmd.append("--no-input")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return True
        print(f"[qgis-sdk bootstrap] pip install failed: {result.stderr}")
    except Exception as e:
        print(f"[qgis-sdk bootstrap] pip install exception: {e}")

    # Try offline wheel if bundled
    wheels_dir = _get_plugin_dir() / "wheels"
    if wheels_dir.exists():
        for wheel in wheels_dir.glob("qgis_sdk*.whl"):
            try:
                with zipfile.ZipFile(wheel) as z:
                    z.extractall(target_dir)
                print(f"[qgis-sdk bootstrap] installed from wheel {wheel}")
                return True
            except Exception as e:
                print(f"[qgis-sdk bootstrap] wheel install failed {wheel}: {e}")

    # Try download from PyPI via urllib (no pip)
    try:
        # Simplified — fetch latest version JSON from PyPI
        import json
        with urllib.request.urlopen("https://pypi.org/pypi/qgis-sdk/json", timeout=15) as resp:
            data = json.loads(resp.read().decode())
            version = data["info"]["version"]
            # Find wheel url
            for url_info in data["urls"]:
                if url_info["packagetype"] == "bdist_wheel" and url_info["python_version"] == "py3":
                    wheel_url = url_info["url"]
                    wheel_path = target_dir / "qgis_sdk_tmp.whl"
                    print(f"[qgis-sdk bootstrap] downloading {wheel_url}")
                    urllib.request.urlretrieve(wheel_url, wheel_path)
                    with zipfile.ZipFile(wheel_path) as z:
                        z.extractall(target_dir)
                    wheel_path.unlink(missing_ok=True)
                    return True
    except Exception as e:
        print(f"[qgis-sdk bootstrap] download failed: {e}")

    return False

def ask_user_to_install(parent=None):
    try:
        from qgis.PyQt.QtWidgets import QMessageBox
        msg = QMessageBox(parent)
        msg.setWindowTitle("qgis-sdk required")
        msg.setText(
            "This plugin requires qgis-sdk.\n\n"
            "Install automatically?\n\n"
            "Yes = auto-install via pip to plugin's extlibs (no admin needed)\n"
            "No = show manual instructions"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Yes)
        ret = msg.exec()
        if ret == QMessageBox.Yes:
            return "auto"
        elif ret == QMessageBox.No:
            return "manual"
        else:
            return "cancel"
    except Exception:
        # No Qt — console fallback
        print("qgis-sdk required. Install via: pip install qgis-sdk")
        return "manual"

def show_manual_instructions(parent=None):
    try:
        from qgis.PyQt.QtWidgets import QMessageBox
        QMessageBox.information(
            parent,
            "Install qgis-sdk",
            "Please install qgis-sdk manually:\n\n"
            "pip install qgis-sdk\n"
            "or\n"
            "conda install -c conda-forge qgis-sdk\n\n"
            "Then restart QGIS.\n\n"
            "Docs: https://archont561.github.io/qgis-rs/getting-started/python-sdk/"
        )
    except Exception:
        print("Manual install: pip install qgis-sdk")

def ensure_qgis_sdk(auto_install=True, ask_user=True, parent=None, target_dir=None):
    """
    Ensure qgis_sdk is importable. If not, try to install.

    Returns True if qgis_sdk now importable, False otherwise.
    """
    if is_qgis_sdk_installed():
        return True

    # Try extlibs already exists
    _ensure_extlibs_in_path()
    if is_qgis_sdk_installed():
        return True

    # Try vendor/ (fully bundled at build time)
    vendor = _get_plugin_dir() / "vendor"
    if vendor.exists() and str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
        if is_qgis_sdk_installed():
            return True

    if not auto_install:
        if ask_user:
            show_manual_instructions(parent)
        return False

    if ask_user:
        choice = ask_user_to_install(parent)
        if choice == "cancel":
            return False
        if choice == "manual":
            show_manual_instructions(parent)
            return False

    # Auto install
    extlibs = _get_extlibs_dir()
    _ensure_extlibs_in_path()
    success = install_from_pip(target_dir=extlibs, auto_confirm=True)
    if success and is_qgis_sdk_installed():
        return True

    if ask_user:
        show_manual_instructions(parent)
    return False
```

**`qgis_sdk/runtime.py` — ensure() for installed qgis_sdk:**

```python
# qgis_sdk/runtime.py
def ensure_qgis_sdk(auto_install=True, ask_user=True):
    # Same logic but when qgis_sdk already importable, ensures _core Rust ext
    try:
        from . import _core
        return True
    except ImportError:
        # Pure-python fallback is okay — no need to install Rust
        return True

def install_core_runtime():
    # Tries to install Rust _core via pip if not present, else uses pure-py
    pass
```

**Plugin `__init__.py` template — self-registering:**

```python
# my_plugin/__init__.py — generated by scaffold with --bundle
def _bootstrap():
    import sys, pathlib
    plugin_dir = pathlib.Path(__file__).parent
    # 1. Try extlibs
    extlibs = plugin_dir / "extlibs"
    if extlibs.exists() and str(extlibs) not in sys.path:
        sys.path.insert(0, str(extlibs))
    # 2. Try vendor (bundled)
    vendor = plugin_dir / "vendor"
    if vendor.exists() and str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))

    try:
        import qgis_sdk
        return qgis_sdk
    except ImportError:
        pass

    # 3. Try bootstrap.py (vendored tiny helper)
    try:
        from .bootstrap import ensure_qgis_sdk
        if ensure_qgis_sdk(auto_install=True, ask_user=True):
            import qgis_sdk
            return qgis_sdk
    except Exception as e:
        print(f"[my_plugin] bootstrap failed: {e}")

    return None

_qgis_sdk = _bootstrap()

if _qgis_sdk is None:
    # Minimal classFactory that shows warning and returns None
    def classFactory(iface):
        try:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.warning(
                None,
                "My Plugin",
                "qgis-sdk not installed and auto-install failed.\n\n"
                "Please install manually:\n"
                "pip install qgis-sdk\n"
                "or\n"
                "conda install -c conda-forge qgis-sdk"
            )
        except Exception:
            print("qgis-sdk not installed")
        return None
else:
    # Normal declarative plugin — uses qgis_sdk
    from qgis_sdk import plugin, toolbar, action

    @plugin(
        name="My Plugin",
        version="0.1.0",
        description="...",
        author="Me",
        qgis_min_version="3.28"
    )
    class MyPlugin:
        @toolbar("My Toolbar")
        @action(tooltip="Run")
        def run(self, iface):
            iface.messageBar().pushMessage("Hello from My Plugin!")

    def classFactory(iface):
        return MyPlugin(iface)
```

**CLI for author — bundling:**

```bash
# New commands
qgis-plugin vendor --output my_plugin/vendor
# Copies pure-python qgis_sdk (without _core) into my_plugin/vendor/qgis_sdk
# So zip is self-contained, no pip needed at runtime

qgis-plugin vendor --output my_plugin/extlibs --wheel
# Copies wheel into my_plugin/wheels/ for offline install

qgis-plugin package --bundle
# Equivalent to: vendor + package
# Creates my_plugin.zip that includes vendor/ or wheels/ + bootstrap.py

qgis-plugin package --bundle --offline
# Includes wheel for offline

qgis-plugin bootstrap --output my_plugin/bootstrap.py
# Copies tiny bootstrap.py (single file) into plugin
```

**`qgis_sdk` installer helper:**

```python
# qgis_sdk/installer.py
class Installer:
    def __init__(self, plugin_dir=None):
        self.plugin_dir = pathlib.Path(plugin_dir or pathlib.Path(__file__).parent.parent)

    def is_installed(self): ...
    def install(self, target="extlibs", offline=False): ...
    def uninstall(self): ...
    def ensure(self, auto_install=True, ask_user=True): ...
    def show_dialog(self, parent=None): ... # QMessageBox with progress

def ensure_qgis_sdk(...): # convenience
    return Installer().ensure(...)
```

**QGIS Plugin Repository — metadata.txt:**

```ini
[general]
name=My Plugin
...
# Tell QGIS about dependency (QGIS 3.32+ supports plugin_dependencies)
plugin_dependencies=qgis_sdk_plugin  # if we publish a qgis-sdk as QGIS plugin wrapper
# Or custom key for our bootstrap to read
qgis_sdk_min_version=0.1.0
qgis_sdk_auto_install=True
```

Alternatively, publish `qgis-sdk` itself as a QGIS plugin (thin wrapper that installs pip package) — so other plugins can depend on it via `plugin_dependencies`.

**Flow for user who installs zip:**

1. User downloads `my_plugin.zip` from QGIS Plugin Repository (or GitHub release).
2. QGIS Plugin Manager extracts to `.../python/plugins/my_plugin/`.
3. QGIS calls `classFactory(iface)`:
   - `bootstrap` checks `extlibs/qgis_sdk` → not found
   - Checks `vendor/qgis_sdk` → if `--bundle` was used, found → import → works → no dialog
   - If not bundled, shows dialog "qgis-sdk required, install now?"
   - If Yes: pip install to `extlibs` (user-local, no admin), add to path, import, continue
   - If No: show manual instructions
4. Plugin registers itself via declarative decorators, toolbar appears.

**Offline / no pip case:**
- If `wheels/` contains wheel, installer extracts it — no internet, no pip needed.
- If `vendor/` contains full qgis_sdk pure-py, import works immediately — fully offline, no install step.

**For Rust _core:**
- Pure-python fallback is always available, so vendored version works without Rust.
- If user has Rust and wants speed, `qgis_sdk.runtime.install_core_runtime()` can try pip install with compiled extension, or `qgis-plugin` Rust binary provides it.

---

## 7. Migration Steps (Incremental, no big bang) — Updated with Bootstrap

### Phase 1 — Package split + Bootstrap (1-2 days)

- [ ] Create `packages-py/` and `packages-node/` dirs
- [ ] Move `packages/qgis-sdk` → `packages-py/qgis-sdk`, clean
- [ ] Move `packages/qgis-sdk-bridge` → `packages-node/qgis-sdk-bridge`, delete stray py files, fix `package.json` exports
- [ ] Move `packages/qgis-node` → `packages-node/qgis-node`, `packages/qgis-rs` → `packages-py/qgis-rs`
- [ ] Update root `Cargo.toml` workspace: `members = ["packages-rs/*", "packages-py/qgis-sdk"]`
- [ ] Update `pyproject.toml` maturin manifest paths
- [ ] Update CI: test `packages-py/*` with `pytest`, `packages-node/*` with `npm test`
- [ ] Create `packages-py/qgis-sdk/src/qgis_sdk/bootstrap.py` — tiny vendored helper (pure-py, <300 LOC)
- [ ] Create `packages-py/qgis-sdk/src/qgis_sdk/installer.py` — Installer class with pip + wheel + download
- [ ] Update `scaffold.py` to generate `bootstrap.py` + `__init__.py` with self-registering logic + `extlibs/` gitignore
- [ ] Verify `pip install -e packages-py/qgis-sdk` and `npm install` in bridge still work

### Phase 2 — Tests mimic src (1 day)

- [ ] For each `src/qgis_sdk/*.py`, create `tests/qgis_sdk/<module>/test_*.py`
- [ ] Move existing `tests/test_network.py` → `tests/qgis_sdk/network/test_manager.py` + `test_session.py` etc, but keep old as shim that imports new
- [ ] Same for `test_tasks.py` → `tests/qgis_sdk/tasks/test_task.py`, `test_celery_api.py`
- [ ] Add `tests/qgis_sdk/bridge/test_description.py`, `test_window.py`
- [ ] Update `pyproject.toml` `testpaths = ["tests"]`
- [ ] Ensure `pytest` still finds all via `pythonpath = ["src"]`

### Phase 3 — Bridge description loader (2-3 days)

- [ ] Create `packages-py/qgis-sdk/src/qgis_sdk/bridge/description.py` with `BridgeDescription`, `MethodDescription`
- [ ] Create `bridge/decorators.py` with `@bridge`, `@method`, `@signal`
- [ ] Create `bridge/runtime.py` with `BridgeRuntime` that registers QWebChannel and injects `window.__QGIS_BRIDGE_DESCRIPTION__ = {...}`
- [ ] Create `bridge/window.py` with `BridgeWindow` (EventTarget-like) for Python side
- [ ] In `packages-node/qgis-sdk-bridge/src/description.ts`: `loadDescription()`, `createBridgeFromDescription()`
- [ ] In `window.ts`: implement `QgisBridge extends EventTarget` with `CONNECTING/OPEN/CLOSED`, `onopen/onmessage/onerror/onclose`, `send()`, `close()`, `addEventListener`, `call()`, Proxy for direct method access
- [ ] Update `loader.ts` to try `window.__QGIS_BRIDGE_DESCRIPTION__` first, then QWebChannel
- [ ] CLI: add `qgis-plugin bridge describe --bridge X --output bridge.json`
- [ ] Keep `generate` as optional for TS types, but not required
- [ ] Update scaffold to generate `web/bridge.json` not `bridge.d.ts` by default, and JS uses `createBridge()` without import

### Phase 4 — Declarative decorator API (3-4 days)

- [ ] Create `qgis_sdk/plugin/registry.py` global registry
- [ ] Create `qgis_sdk/plugin/decorators.py` with `@plugin`, `@toolbar`, `@action`, `@menu`, `@setting`
- [ ] Refactor `plugin.py` to use registry: `Plugin` class becomes thin wrapper, `classFactory` generated from registry
- [ ] Update `algorithm/decorators.py` to use `@algorithm` + `@param` declarative, inject params into `process`
- [ ] Update `network/decorators.py` with `@with_auth`, `@session`
- [ ] Update `tasks/decorators.py` already celery-like, but ensure `@task` works without class
- [ ] Update `bridge/decorators.py` as above
- [ ] Update `scaffold.py` to generate new declarative examples:
  ```python
  @plugin(name="...")
  class MyPlugin:
      @toolbar("...")
      @action(tooltip="...")
      def run(self, iface): ...
  ```
- [ ] Ensure old class-based API still works via shim (deprecation warning)

### Phase 5 — Bootstrap & Vendor CLI (1-2 days)

- [ ] Implement `qgis-plugin vendor --output my_plugin/vendor` — copies pure-py `qgis_sdk` into vendor
- [ ] Implement `qgis-plugin vendor --output my_plugin/extlibs --wheel` — copies wheel into `wheels/`
- [ ] Implement `qgis-plugin package --bundle` — vendor + package
- [ ] Implement `qgis-plugin bootstrap --output my_plugin/bootstrap.py`
- [ ] Test in clean QGIS profile without qgis-sdk installed: install zip, trigger auto-install dialog, verify toolbar appears
- [ ] Test offline: zip with `wheels/` and `vendor/`, no internet, no pip

### Phase 6 — Docs & Examples (1 day)

- [ ] Update `apps/docs/src/content/docs/reference/bridge.mdx` to show description loader + window-like API
- [ ] Update `reference/network.mdx` to show requests-like + Session
- [ ] Update `reference/tasks.mdx` to show celery-like
- [ ] Add `guides/declarative-api.mdx` showing all decorators
- [ ] Add `guides/bridge-window-api.mdx` showing EventSource/WebSocket-like
- [ ] Add `guides/plugin-distribution.mdx` showing bundle, bootstrap, auto-install, offline wheel, `plugin_dependencies`
- [ ] Update `getting-started/python-sdk.mdx` with new layout and `ensure_qgis_sdk()` pattern

---

## 8. Example Final Plugin (Declarative + Self-Installing)

```python
# my_plugin/__init__.py
from qgis_sdk import plugin, toolbar, action, task, bridge, method, signal, setting
from qgis_sdk.network import Session
from qgis_sdk.tasks import chain

@plugin(
    name="My Plugin",
    version="0.1.0",
    description="Does useful things declaratively",
    author="Me",
    email="me@example.com",
    qgis_min_version="3.28",
    category="Vector"
)
class MyPlugin:
    @setting(default=10.0, persist=True)
    def distance(self): return 10.0

    @toolbar("My Toolbar")
    @action(tooltip="Run buffer", icon="icons/buffer.svg")
    def run_buffer(self, iface, distance: float):
        # Network — requests-like
        session = Session(auth_cfg="my_auth", headers={"User-Agent": "MyPlugin"})
        resp = session.get("https://example.com/api", params={"distance": distance})
        resp.raise_for_status()

        # Tasks — celery-like
        result = self.buffer_task.delay(distance)
        iface.messageBar().pushMessage(f"Task {result.id} started, state={result.state}")

    @task("Buffer task", bind=True, can_cancel=True)
    def buffer_task(self, distance: float):
        self.set_progress(0)
        # heavy work
        for i in range(100):
            self.set_progress(i)
            if self.is_canceled():
                return None
        return {"distance": distance}

    @bridge(name="my_bridge")
    class Bridge:
        @method(return_type=dict)
        def get_layer(self, layer_id: str) -> dict:
            return {"name": layer_id, "count": 42}

        @method()
        def log(self, msg: str) -> str:
            print(f"[JS] {msg}")
            return "ok"

        @signal()
        def layer_changed(self, layer_id: str):
            pass

    @bridge.window
    def on_window(self, window):
        # window is EventTarget-like
        window.add_event_listener("message", lambda e: print(e.data))
        window.add_event_listener("layer_changed", lambda e: print(e.detail))
        window.send({"ready": True})

def classFactory(iface):
    return MyPlugin(iface)
```

```typescript
// web/app.ts — no codegen needed, windows-like
import { createBridge, QgisBridge } from '@qgis-sdk/bridge';

const bridge = await createBridge(); // loads description from window.__QGIS_BRIDGE_DESCRIPTION__

bridge.addEventListener("open", () => console.log("bridge open, state:", bridge.readyState));
bridge.addEventListener("message", (e) => console.log("message", e.data));
bridge.addEventListener("layer_changed", (e) => console.log("layer changed", e.detail));

bridge.onmessage = (e) => console.log("onmessage", e.data);
bridge.onerror = (e) => console.error(e);

const layer = await bridge.get_layer("my_layer"); // from description, typed if bridge.json loaded
await bridge.call("log", "hello from JS");

bridge.send({action: "buffer"});
bridge.postMessage({action: "buffer"});

console.log(bridge.readyState === QgisBridge.OPEN);
```

---

## 9. Risks & Mitigations

- **Breaking change for existing plugins:** Keep old `Plugin` base class as shim that delegates to registry, with deprecation warning. Scaffold generates new API but old still works.
- **Rust workspace split:** Keep `Cargo.toml` at root with `members = ["packages-rs/*", "packages-py/qgis-sdk"]` so `maturin develop` still works. For `packages-node`, use `napi-rs` or keep JS fallback.
- **Bridge description JSON injection:** QWebChannel `runJavaScript` may not be ready immediately — inject via `setHtml` with `<script>window.__QGIS_BRIDGE_DESCRIPTION__ = ...</script>` before loading page.
- **Tests mirroring src:** Need to update `pyproject.toml` and ensure CI caches. Use `pytest --import-mode=importlib` to avoid import conflicts.

---

## 10. Deliverables Checklist

- [ ] `packages-py/` and `packages-node/` layout
- [ ] `qgis-bridge` Python package with description loader (no codegen required)
- [ ] `QgisBridge extends EventTarget` with `readyState`, `onopen/onmessage/onerror/onclose`, `send()`, `close()`, `addEventListener`, `call()`, Proxy for methods — feels like `WebSocket`/`EventSource`/`window`
- [ ] `tests/` mirrors `src/` for each package
- [ ] `qgis-sdk` declarative API via decorators: `@plugin`, `@toolbar`, `@action`, `@task`, `@bridge`, `@method`, `@signal`, `@setting`, `@algorithm`, `@param`
- [ ] Scaffold generates new declarative examples
- [ ] Docs updated: `guides/declarative-api.mdx`, `guides/bridge-window-api.mdx`
- [ ] All 112+ tests passing, plus new bridge description tests
```

