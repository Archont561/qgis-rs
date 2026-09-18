# Refactor Plan — Split packages-py / packages-bun, declarative decorator API, windows-like bridge + complete QGIS Web API

**Date:** 2026-09-18 (updated: bun + qgis web API)
**Branch:** `arena/01a0b44f-qgis-rs`
**Goal:** Make repo maintainable, language-separated, declarative, testable, with bridge that feels like native browser APIs (EventSource/WebSocket/window) and exposes **complete QGIS API to JS** so webview can trigger jobs, show messages, do network via QGIS, load layers without user writing bridge boilerplate each time. Use **bun** instead of node/npm for all JS tooling.

> **Status (2026-09-18, delivered):** the layout split landed, with one correction to
> the plan below — the language packages are named `py-packages/` and `ts-packages/`
> (not `packages-py/`/`packages-bun/`), and *all* Rust moved to `crates/`:
> `crates/qgis-py` (python bindings), `crates/qgis-sdk` (the sdk's Rust core, kept as
> a crate because `crates/qgis-node` depends on it) and `crates/qgis-node`.
> `packages-bun/qgis-node` was deleted in favour of `ts-packages/qgis-node`;
> `packages-bun/qgis-sdk-bridge` became `ts-packages/qgis-sdk-bridge` and the sdk's TS
> sources live in `py-packages/qgis-sdk/ts/`. maturin reaches the crates through
> `[tool.maturin].manifest-path`, so the py-packages hold no Rust. Import names
> (`qgis_rs`, `qgis_sdk`, `qgis_rs._core`) and the npm package name `qgis-node` are
> unchanged. See [.knowledge/log.md](./.knowledge/log.md).

---

## 0. Current State Pain Points

- `packages/qgis-sdk` mixes Python + Rust (`src/` Python, `src_rs/` Rust bins) — confusing for maturin + bun.
- `packages/qgis-sdk-bridge` is JS-only but lives next to Python, and its `src/` contains stray Python files (copy-paste bug: `__init__.py`, `bridge.py` etc inside bridge package).
- `packages/qgis-node` and `packages/qgis-rs` are Rust workspaces with JS/Python wrappers but not aligned.
- `tests/` is flat (`test_network.py`, `test_tasks.py`) not mirroring `src/qgis_sdk/` structure → hard to find, no per-module coverage.
- Bridge today: Python class → codegen `bridge.d.ts` + `bridge.js` package. User must run `qgis-plugin bridge generate` after every change. No runtime loading of description. JS API is callback-based with Promise wrapper, not windows-like. **No built-in QGIS API** — user must write `get_layer`, `show_message`, `run_task`, `network_fetch` etc manually every time for each plugin.
- Plugin API: class-based `Plugin` with `@toolbar/@action` but still imperative `init_gui`. Want mostly decorators, like FastAPI / Celery / click.
- JS tooling uses `npm`/`node` — slow, fragmented. Want `bun` for install, run, test, build, workspaces (bun is 10x faster, native TS, built-in bundler, `bun:test`).

---

## 1. Proposed New Layout (bun)

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
│   │   │   │   ├── runtime.py    # BridgeRuntime — loads description, registers QWebChannel, injects QgisApi
│   │   │   │   ├── window.py     # Window-like object (EventSource/WebSocket API)
│   │   │   │   ├── qgis_api.py   # QgisApi — built-in QGIS methods exposed to JS (layers, tasks, messageBar, network, project, iface)
│   │   │   │   ├── qgis_api/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── layers.py      # addVector, addRaster, list, active, remove, zoom
│   │   │   │   │   ├── project.py     # addLayer, removeLayer, crs, path, write
│   │   │   │   │   ├── message.py     # info/warning/critical + messageBar.pushMessage
│   │   │   │   │   ├── tasks.py       # run, list, cancel — triggers @task decorated jobs
│   │   │   │   │   ├── network.py     # fetch via QGIS NAM with auth
│   │   │   │   │   ├── iface.py       # zoomToLayer, activeLayer, etc
│   │   │   │   │   ├── settings.py    # get/set plugin settings
│   │   │   │   │   └── processing.py  # run alg via QgsProcessingAlgRunnerTask
│   │   │   │   └── loader.py     # load_bridge_description()
│   │   │   ├── ui/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dialog.py
│   │   │   │   ├── webview.py    # auto-injects qgis API + description + qwebchannel.js
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
│   │   │   │   │   ├── test_window.py
│   │   │   │   │   └── test_qgis_api.py
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
├── packages-bun/                 # all JS/TS packages use bun (bun workspaces, bun:test, bun build, bun --bun)
│   ├── qgis-sdk-bridge/          # @qgis-sdk/bridge — JS/TS bridge, windows-like, bun
│   │   ├── src/
│   │   │   ├── index.ts          # createBridge, Bridge as EventTarget, exports qgis
│   │   │   ├── window.ts         # BridgeWindow extends EventTarget (EventSource-like)
│   │   │   ├── loader.ts
│   │   │   ├── qgis.ts           # Qgis global API — high-level JS SDK for QGIS (layers, tasks, messageBar, network, project)
│   │   │   ├── qgis/
│   │   │   │   ├── layers.ts     # qgis.layers.addVector, list, active, signals
│   │   │   │   ├── project.ts    # qgis.project.addLayer, crs, etc
│   │   │   │   ├── message.ts    # qgis.message.info/warning/critical + messageBar
│   │   │   │   ├── tasks.ts      # qgis.tasks.run, list, cancel
│   │   │   │   ├── network.ts    # qgis.network.fetch via QGIS NAM
│   │   │   │   ├── iface.ts      # qgis.iface.zoomToLayer etc
│   │   │   │   ├── settings.ts   # qgis.settings.get/set
│   │   │   │   └── processing.ts # qgis.processing.run
│   │   │   ├── react.ts
│   │   │   ├── vue.ts
│   │   │   ├── svelte.ts
│   │   │   ├── webcomponents.ts
│   │   │   └── description.ts    # loads BridgeDescription JSON from Python
│   │   ├── tests/
│   │   │   ├── bridge/
│   │   │   │   ├── test_window.test.ts
│   │   │   │   ├── test_description.test.ts
│   │   │   │   ├── test_loader.test.ts
│   │   │   │   └── test_qgis.test.ts
│   │   │   └── package.json      # uses bun:test, type: module, scripts: bun test, bun run build
│   │   ├── bun.lockb (or root)
│   │   └── tsconfig.json
│   │
│   ├── qgis-sdk/                 # @qgis-sdk/sdk — high-level JS SDK that wraps bridge (for webviews), bun build
│   │   ├── src/
│   │   │   ├── index.ts          # exports qgis, createBridge, QgisBridge, hooks
│   │   │   ├── qgis.ts           # qgis global singleton
│   │   │   └── framework/        # React/Vue/Svelte adapters
│   │   └── package.json
│   │
│   ├── qgis-sdk-cli/             # bun wrapper for qgis-plugin binary (bun build --compile -> single binary)
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   └── bin.ts            # bun build --compile to qgis-plugin binary
│   │   └── package.json
│   │
│   └── qgis-rs-bun/              # JS wrapper for qgis-rs, built with bun
│       ├── src/
│       └── tests/
│
├── packages-rs/
│   ├── qgis-sdk-core/            # Rust core for qgis-sdk (metadata, scaffold)
│   │   └── src/
│   ├── qgis-rs-core/
│   └── qgis-cli-core/
│
├── package.json                  # root bun workspaces: ["packages-bun/*", "apps/*"], scripts use bun
├── bun.lockb
└── apps/
    └── docs/                     # Astro docs, run with bun --bun astro dev
```

**Migration steps (bun):**
1. `mkdir -p packages-py packages-bun packages-rs`
2. `git mv packages/qgis-sdk packages-py/qgis-sdk`
3. `git mv packages/qgis-sdk-bridge packages-bun/qgis-sdk-bridge` (and clean stray py files)
4. `git mv packages/qgis-node packages-bun/qgis-rs-bun` etc.
5. Root `package.json`:
   ```json
   {
     "workspaces": ["packages-bun/*", "apps/*"],
     "scripts": {
       "build": "bun run --filter '*' build",
       "test": "bun test",
       "dev": "bun --bun astro dev --filter docs"
     },
     "packageManager": "bun"
   }
   ```
6. `bun install` (replaces npm/pnpm), `bun run build`, `bun test` — bun handles TS natively, no ts-node needed.
7. Update root `Cargo.toml` workspace: `members = ["packages-rs/*", "packages-py/qgis-sdk"]`
8. Update `pyproject.toml` `tool.maturin.manifest-path` to `../../packages-rs/qgis-sdk-core/Cargo.toml`
9. Update CI to test `packages-py/*` with `pytest` and `packages-bun/*` with `bun test` (instead of npm). Use `oven/bun:latest` image.
10. Update `apps/docs` `astro.config.mjs` to use `vite` with bun — `bun --bun astro dev`, `bun --bun astro build`.
11. Add `bun.lockb` to git, update `.gitignore` to not ignore it.

**Why bun not node:**
- `bun install` 10-20x faster than npm, workspaces native.
- `bun:test` built-in, no jest/vitest config needed (but vitest also works with bun).
- `bun build` bundles TS to ESM/CJS with single command, no tsup/rollup.
- `bun --bun` runs TS directly, no tsx.
- `bun build --compile` can compile JS CLI to single binary (for `qgis-plugin` JS wrapper).
- Better DX for QGIS plugin devs who are not JS experts — one tool.

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
    def __init__(self, description: BridgeDescription, impl_instance, qgis_api=None):
        self.description = description
        self.impl = impl_instance
        self.qgis_api = qgis_api or QgisApi()  # built-in API
        self._channel = None
        self._window = None

    def register(self, webview):
        # Creates QWebChannel, registers impl + qgis_api
        channel = QWebChannel()
        channel.registerObject(self.description.name, self.impl)
        channel.registerObject("qgis", self.qgis_api)  # <-- built-in QGIS API
        webview.page().setWebChannel(channel)
        # Inject description JSON + qgis api description into window
        json_str = self.description.to_json()
        qgis_json = self.qgis_api.description.to_json()
        webview.page().runJavaScript(f"window.__QGIS_BRIDGE_DESCRIPTION__ = {json_str}; window.__QGIS_API_DESCRIPTION__ = {qgis_json}")

    def to_window(self):
        # Returns window-like object for Python → JS
        return BridgeWindow(self)
```

User can still codegen if wants, but default is runtime.

**CLI change:**
- `qgis-plugin bridge describe --bridge my_plugin:MyBridge --output web/bridge.json` → outputs JSON description, not TS.
- `qgis-plugin bridge generate` becomes optional, for TS types if user wants static typing.
- JS can work without any generated file: `const bridge = await createBridge()` loads description from `window.__QGIS_BRIDGE_DESCRIPTION__`.

---

## 2b. Complete QGIS API Exposed to JS (not just user bridge)

### Problem
- Today user must define `get_layer`, `add_layer`, `show_message`, `run_task`, `fetch` etc for every plugin — boilerplate.
- JS in QWebEngineView cannot do QGIS things without Python bridge methods. Want high-level `window.qgis` that already can do everything.

### Desired: built-in `qgis` global, like `window.qgis`

**Python side — QgisApi class with all common QGIS operations:**

```python
# qgis_sdk/bridge/qgis_api.py
from dataclasses import dataclass
from qgis_sdk.bridge.decorators import method, signal

class QgisApi:
    """
    Built-in QGIS API exposed to JS automatically.
    Registered as "qgis" QWebChannel object alongside user bridge.
    JS can call window.qgis.* without user defining bridge.
    """

    def __init__(self, iface=None, plugin=None):
        self.iface = iface
        self.plugin = plugin
        self._task_manager = None

    # ---- MessageBar / Message ----
    @method()
    def message_info(self, title: str, message: str, duration: int = 5) -> bool:
        self.iface.messageBar().pushMessage(title, message, level=Qgis.Info, duration=duration)
        return True

    @method()
    def message_warning(self, title: str, message: str, duration: int = 5) -> bool: ...

    @method()
    def message_critical(self, title: str, message: str, duration: int = 5) -> bool: ...

    @method()
    def message_success(self, title: str, message: str, duration: int = 5) -> bool: ...

    # ---- Layers ----
    @method(return_type=dict)
    def layers_list(self) -> list:
        # returns [{"id": ..., "name": ..., "type": "vector/raster", "crs": ..., "featureCount": ...}]
        from qgis.core import QgsProject
        return [{"id": l.id(), "name": l.name(), "type": "vector" if l.type()==0 else "raster", "crs": l.crs().authid()} for l in QgsProject.instance().mapLayers().values()]

    @method(return_type=dict)
    def layers_active(self) -> dict | None:
        layer = self.iface.activeLayer()
        return {"id": layer.id(), "name": layer.name()} if layer else None

    @method(return_type=dict)
    def layers_add_vector(self, path: str, name: str = "", provider: str = "ogr") -> dict:
        from qgis.core import QgsVectorLayer, QgsProject
        layer = QgsVectorLayer(path, name or path, provider)
        if not layer.isValid():
            raise ValueError(f"Failed to load vector layer {path}")
        QgsProject.instance().addMapLayer(layer)
        return {"id": layer.id(), "name": layer.name()}

    @method(return_type=dict)
    def layers_add_raster(self, path: str, name: str = "", provider: str = "gdal") -> dict:
        from qgis.core import QgsRasterLayer, QgsProject
        layer = QgsRasterLayer(path, name or path, provider)
        if not layer.isValid():
            raise ValueError(f"Failed to load raster {path}")
        QgsProject.instance().addMapLayer(layer)
        return {"id": layer.id(), "name": layer.name()}

    @method()
    def layers_remove(self, layer_id: str) -> bool:
        from qgis.core import QgsProject
        QgsProject.instance().removeMapLayer(layer_id)
        return True

    @method()
    def layers_zoom_to(self, layer_id: str) -> bool:
        from qgis.core import QgsProject
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer:
            self.iface.zoomToActiveLayer() if layer == self.iface.activeLayer() else self.iface.mapCanvas().setExtent(layer.extent())
            self.iface.mapCanvas().refresh()
        return True

    @method()
    def layers_set_active(self, layer_id: str) -> bool:
        from qgis.core import QgsProject
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer:
            self.iface.setActiveLayer(layer)
        return True

    @signal()
    def layer_added(self, layer_id: str): ...

    @signal()
    def layer_removed(self, layer_id: str): ...

    # ---- Project ----
    @method(return_type=dict)
    def project_info(self) -> dict:
        from qgis.core import QgsProject
        p = QgsProject.instance()
        return {"path": p.fileName(), "crs": p.crs().authid(), "title": p.title()}

    @method()
    def project_write(self) -> bool:
        from qgis.core import QgsProject
        return QgsProject.instance().write()

    @method(return_type=str)
    def project_crs(self) -> str:
        from qgis.core import QgsProject
        return QgsProject.instance().crs().authid()

    @method()
    def project_set_crs(self, authid: str) -> bool:
        from qgis.core import QgsProject, QgsCoordinateReferenceSystem
        QgsProject.instance().setCrs(QgsCoordinateReferenceSystem(authid))
        return True

    # ---- Tasks / Jobs ----
    @method(return_type=dict)
    def tasks_run(self, task_name: str, params: dict = None) -> dict:
        """
        Triggers a @task decorated job by name.
        params passed to task.
        Returns {"task_id": ..., "status": "queued"}
        JS can listen to task_progress / task_finished signals.
        """
        # Lookup from plugin registry
        from qgis_sdk.plugin.registry import registry
        wrapper = registry.get_task(task_name)
        if not wrapper:
            raise ValueError(f"Task {task_name} not found")
        result = wrapper.delay(**(params or {}))
        return {"task_id": result.id, "status": result.state}

    @method(return_type=list)
    def tasks_list(self) -> list:
        # List running tasks
        from qgis.core import QgsApplication
        tm = QgsApplication.taskManager()
        return [{"id": t.id(), "description": t.description(), "status": t.status()} for t in tm.tasks()]

    @method()
    def tasks_cancel(self, task_id: int) -> bool:
        from qgis.core import QgsApplication
        tm = QgsApplication.taskManager()
        for t in tm.tasks():
            if str(t.id()) == str(task_id):
                t.cancel()
                return True
        return False

    @signal()
    def task_progress(self, task_id: str, progress: float): ...

    @signal()
    def task_finished(self, task_id: str, result: dict): ...

    # ---- Network via QGIS ----
    @method(return_type=dict)
    def network_fetch(self, url: str, method: str = "GET", headers: dict = None, body: str = None, auth_cfg: str = None) -> dict:
        """
        Makes network request via QgsNetworkAccessManager (respects QGIS proxy, auth).
        Returns {"status": 200, "headers": {}, "body": "...", "json": {...} if json}
        """
        from qgis_sdk.network import Session
        sess = Session(auth_cfg=auth_cfg, headers=headers or {})
        resp = sess.request(method, url, data=body)
        return {"status": resp.status_code, "headers": dict(resp.headers), "body": resp.text, "ok": resp.ok}

    # ---- Iface ----
    @method()
    def iface_zoom_to_layer(self, layer_id: str) -> bool:
        return self.layers_zoom_to(layer_id)

    @method()
    def iface_show_message(self, title: str, message: str, level: int = 0, duration: int = 5) -> bool:
        return self.message_info(title, message, duration)

    # ---- Settings ----
    @method(return_type=str)
    def settings_get(self, key: str, default: str = "") -> str:
        from qgis.core import QgsSettings
        return QgsSettings().value(f"my_plugin/{key}", default)

    @method()
    def settings_set(self, key: str, value: str) -> bool:
        from qgis.core import QgsSettings
        QgsSettings().setValue(f"my_plugin/{key}", value)
        return True

    # ---- Processing ----
    @method(return_type=dict)
    def processing_run(self, alg_id: str, params: dict) -> dict:
        # Runs processing alg via QgsProcessingAlgRunnerTask (background)
        from qgis_sdk.tasks import TaskManager
        # ... simplified
        return {"task_id": "...", "status": "queued"}
```

**JS side — high-level `qgis` global, typed, bun-built:**

```typescript
// packages-bun/qgis-sdk-bridge/src/qgis.ts
import { QgisBridge } from './window';

export interface QgisLayerInfo { id: string; name: string; type: 'vector' | 'raster'; crs: string; }
export interface QgisTaskHandle { task_id: string; status: string; onProgress(cb: (p: number)=>void): void; onFinished(cb: (result: any)=>void): void; cancel(): Promise<boolean>; }

export class QgisAPI extends EventTarget {
  constructor(private _bridge: QgisBridge, private _raw: any) { super(); }

  // Message
  message = {
    info: (title: string, msg: string, duration=5) => this._raw.message_info(title, msg, duration),
    warning: (title: string, msg: string, duration=5) => this._raw.message_warning(title, msg, duration),
    critical: (title: string, msg: string, duration=5) => this._raw.message_critical(title, msg, duration),
    success: (title: string, msg: string, duration=5) => this._raw.message_success(title, msg, duration),
  };
  messageBar = {
    pushMessage: (title: string, text: string, level=0, duration=5) => this._raw.message_info(title, text, duration)
  };

  // Layers
  layers = {
    list: async (): Promise<QgisLayerInfo[]> => this._raw.layers_list(),
    active: async (): Promise<QgisLayerInfo | null> => this._raw.layers_active(),
    addVector: async (path: string, name="", provider="ogr"): Promise<QgisLayerInfo> => this._raw.layers_add_vector(path, name, provider),
    addRaster: async (path: string, name="", provider="gdal"): Promise<QgisLayerInfo> => this._raw.layers_add_raster(path, name, provider),
    remove: async (id: string): Promise<boolean> => this._raw.layers_remove(id),
    zoomTo: async (id: string): Promise<boolean> => this._raw.layers_zoom_to(id),
    setActive: async (id: string): Promise<boolean> => this._raw.layers_set_active(id),
    onAdded: (cb: (e: CustomEvent)=>void) => this.addEventListener('layer_added', cb as any),
    onRemoved: (cb: (e: CustomEvent)=>void) => this.addEventListener('layer_removed', cb as any),
  };

  // Project
  project = {
    info: async () => this._raw.project_info(),
    write: async () => this._raw.project_write(),
    crs: async () => this._raw.project_crs(),
    setCrs: async (authid: string) => this._raw.project_set_crs(authid),
  };

  // Tasks
  tasks = {
    run: async (name: string, params?: any): Promise<QgisTaskHandle> => {
      const res = await this._raw.tasks_run(name, params);
      const handle = { task_id: res.task_id, status: res.status } as QgisTaskHandle;
      // wire progress/finished via signals
      handle.onProgress = (cb) => this._bridge.addEventListener('task_progress', (e: any) => { if (e.detail.task_id===res.task_id) cb(e.detail.progress); });
      handle.onFinished = (cb) => this._bridge.addEventListener('task_finished', (e: any) => { if (e.detail.task_id===res.task_id) cb(e.detail.result); });
      handle.cancel = () => this._raw.tasks_cancel(res.task_id);
      return handle;
    },
    list: async () => this._raw.tasks_list(),
    cancel: async (id: string) => this._raw.tasks_cancel(id),
  };

  // Network via QGIS
  network = {
    fetch: async (url: string, opts: {method?: string, headers?: any, body?: string, authCfg?: string} = {}) => {
      const res = await this._raw.network_fetch(url, opts.method||'GET', opts.headers||{}, opts.body||null, opts.authCfg||null);
      return {
        ok: res.ok,
        status: res.status,
        headers: res.headers,
        text: async () => res.body,
        json: async () => JSON.parse(res.body),
      };
    },
    get: function(url: string, opts={}) { return this.fetch(url, {method: 'GET', ...opts}); },
    post: function(url: string, body?: string, opts={}) { return this.fetch(url, {method: 'POST', body, ...opts}); },
  };

  // Iface
  iface = {
    zoomToLayer: (id: string) => this._raw.iface_zoom_to_layer(id),
    showMessage: (title: string, msg: string, level=0, duration=5) => this._raw.iface_show_message(title, msg, level, duration),
  };

  // Settings
  settings = {
    get: async (key: string, def="") => this._raw.settings_get(key, def),
    set: async (key: string, val: string) => this._raw.settings_set(key, val),
  };

  // Processing
  processing = {
    run: async (algId: string, params: any) => this._raw.processing_run(algId, params),
  };
}

// Global singleton, like window.qgis
export let qgis: QgisAPI;

// Factory — createBridge now also creates qgis global
export async function createQgisBridge(options={}) {
  const bridge = await createBridge(options);
  const rawQgis = await bridge._getRawQgis(); // QWebChannel "qgis" object
  qgis = new QgisAPI(bridge, rawQgis);
  (window as any).qgis = qgis;
  // Also wire signals from Python to JS EventTarget
  bridge.addEventListener('layer_added', (e) => qgis.dispatchEvent(new CustomEvent('layer_added', {detail: e.detail})));
  bridge.addEventListener('task_progress', (e) => qgis.dispatchEvent(new CustomEvent('task_progress', {detail: e.detail})));
  return { bridge, qgis };
}
```

**Usage in webview — no custom bridge needed:**

```typescript
// web/app.ts — using bun
import { createQgisBridge } from '@qgis-sdk/bridge';

const { bridge, qgis } = await createQgisBridge();

// Show message in QGIS messageBar from JS
await qgis.message.info("Hello", "From JS webview!", 5);
await qgis.messageBar.pushMessage("My Plugin", "Layer loaded", 0, 3);

// Load layer from JS — no Python code needed
const layer = await qgis.layers.addVector("/path/to/roads.shp", "Roads");
console.log("Added", layer.id);
await qgis.layers.zoomTo(layer.id);

// List layers
const layers = await qgis.layers.list();
console.log(layers);

// Run background task defined via @task in Python, from JS
const task = await qgis.tasks.run("buffer_task", {distance: 10});
task.onProgress(p => console.log("progress", p));
task.onFinished(result => console.log("finished", result));

// Network via QGIS (uses QGIS proxy, auth)
const resp = await qgis.network.fetch("https://example.com/api", {authCfg: "my_auth"});
const json = await resp.json();

// Project
await qgis.project.setCrs("EPSG:4326");
await qgis.project.write();

// Custom bridge still works alongside qgis global
const custom = await bridge.call("get_layer", "my_layer");
// or
const custom2 = await bridge.get_layer("my_layer");
```

**Python side enables it automatically:**

```python
# qgis_sdk/ui/webview.py
class WebView(QWebEngineView):
    def __init__(self, bridge=None, enable_qgis_api=True, iface=None):
        super().__init__()
        self.bridge_runtime = BridgeRuntime(
            description=bridge._bridge_description if bridge else BridgeDescription(name="bridge", methods=[]),
            impl_instance=bridge,
            qgis_api=QgisApi(iface=iface) if enable_qgis_api else None
        )
        self.bridge_runtime.register(self)

# In plugin
from qgis_sdk.ui import WebView

@toolbar("My Toolbar")
@action(tooltip="Open webview")
def open_webview(self, iface):
    webview = WebView(bridge=self.Bridge(), enable_qgis_api=True, iface=iface)
    webview.load(QUrl.fromLocalFile("/path/to/web/index.html"))
    webview.show()
```

**Permissions — opt-in:**

```python
@plugin(name="My Plugin", permissions=["layers", "project", "tasks", "network", "message", "settings"])
class MyPlugin: ...
# JS will only have access to allowed namespaces. If not specified, all enabled but can be restricted.
# BridgeRuntime checks permissions and only registers allowed methods in QgisApi.
```

**Why this is better than just bridge:**
- 90% of plugins need same operations: show message, load layer, run task, network. Now JS can do it without writing Python bridge method each time.
- Web devs can build full UI in React/Vue/Svelte with bun, using `qgis.*` like they would use `window.fetch` or `navigator.geolocation` — feels native.
- Still extensible: user can add custom `@bridge` methods for domain logic, but `qgis` global covers QGIS primitives.

---

## 3. Bridge as Windows-like Object (EventSource / WebSocket API)

### Desired API

Look at `EventSource` and `WebSocket` and `window`:

- `EventSource`: `addEventListener`, `onmessage`, `onopen`, `onerror`, `close()`, `readyState`
- `WebSocket`: `send()`, `close()`, `addEventListener('message'/'open'/'close'/'error')`, `readyState`, `url`
- `window`: `addEventListener`, `dispatchEvent`, `postMessage`

**Proposed JS BridgeWindow (bun):**

```typescript
// packages-bun/qgis-sdk-bridge/src/window.ts
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

// Usage with bun
// Vanilla
const bridge = await createBridge();
bridge.addEventListener("open", () => console.log("open"));
bridge.addEventListener("message", (e) => console.log(e.data));
bridge.addEventListener("layer_changed", (e) => console.log("layer changed", e.detail));
bridge.onmessage = (e) => console.log(e.data);

const layer = await bridge.get_layer("my_layer"); // method from description
await bridge.call("get_layer", "my_layer");

bridge.send({action: "buffer"});

// React (with bun)
const { bridge, ready } = useQgisBridge(); // returns QgisBridge
useEffect(() => {
  if (!ready) return;
  const handler = (e) => setLayer(e.detail);
  bridge.addEventListener("layer_changed", handler);
  return () => bridge.removeEventListener("layer_changed", handler);
}, [ready]);
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

**For bun:**

```
packages-bun/qgis-sdk-bridge/
  src/
    window.ts
    loader.ts
    description.ts
    qgis.ts
    qgis/layers.ts
  tests/
    bridge/
      window.test.ts      # mirrors src/window.ts
      loader.test.ts
      description.test.ts
      qgis.test.ts        # mirrors src/qgis.ts
```

Use `bun:test` (built-in) — `import { describe, it, expect } from "bun:test"` — with `tests/` mirroring `src/`. Bun runs TS natively, no config. Alternatively vitest works with bun too: `bun --bun vitest`.

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
    category="Vector",
    permissions=["layers", "tasks", "network", "message"]  # for JS qgis API
)
class MyPlugin:
    @setting(default=0.5, persist=True)
    def threshold(self): return 0.5

    @toolbar("My Toolbar")
    @action(tooltip="Run", icon="icons/run.svg")
    def run(self, iface, threshold: float = None):
        layer = iface.activeLayer()
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
        result = self.my_task.delay(42)
        iface.messageBar().pushMessage(f"Task {result.id} started")

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
        window.add_event_listener("message", lambda e: print(e.data))
        window.send({"status": "ready"})

    @toolbar("My Toolbar")
    @action(tooltip="Open webview with qgis API")
    def open_webview(self, iface):
        from qgis_sdk.ui import WebView
        webview = WebView(bridge=self.Bridge(), enable_qgis_api=True, iface=iface, permissions=self._qgis_sdk_metadata.get("permissions"))
        webview.load_html("""
          <script type="module">
            import { createQgisBridge } from './qgis-bridge.js'; // bundled via bun build
            const { qgis } = await createQgisBridge();
            await qgis.message.info("Hello", "Webview ready");
            const layers = await qgis.layers.list();
            console.log(layers);
          </script>
        """)
        webview.show()
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
        cls._qgis_sdk_metadata = metadata
        cls._qgis_sdk_registry = registry
        original_init = getattr(cls, "__init__", lambda self, iface: None)
        def __init__(self, iface):
            self.iface = iface
            self._registry = registry
            original_init(self, iface)
        cls.__init__ = __init__

        def init_gui(self):
            for action_spec in registry.get_actions(cls):
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
    try:
        cmd = [sys.executable, "-m", "pip", "install", "qgis-sdk", "--target", str(target_dir), "--no-deps", "--quiet"]
        if auto_confirm:
            cmd.append("--no-input")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return True
        print(f"[qgis-sdk bootstrap] pip install failed: {result.stderr}")
    except Exception as e:
        print(f"[qgis-sdk bootstrap] pip install exception: {e}")

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

    try:
        import json
        with urllib.request.urlopen("https://pypi.org/pypi/qgis-sdk/json", timeout=15) as resp:
            data = json.loads(resp.read().decode())
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
    if is_qgis_sdk_installed():
        return True
    _ensure_extlibs_in_path()
    if is_qgis_sdk_installed():
        return True
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
    extlibs = _get_extlibs_dir()
    _ensure_extlibs_in_path()
    success = install_from_pip(target_dir=extlibs, auto_confirm=True)
    if success and is_qgis_sdk_installed():
        return True
    if ask_user:
        show_manual_instructions(parent)
    return False
```

**Plugin `__init__.py` template — self-registering:**

```python
# my_plugin/__init__.py — generated by scaffold with --bundle
def _bootstrap():
    import sys, pathlib
    plugin_dir = pathlib.Path(__file__).parent
    extlibs = plugin_dir / "extlibs"
    if extlibs.exists() and str(extlibs) not in sys.path:
        sys.path.insert(0, str(extlibs))
    vendor = plugin_dir / "vendor"
    if vendor.exists() and str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
    try:
        import qgis_sdk
        return qgis_sdk
    except ImportError:
        pass
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
    def classFactory(iface):
        try:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.warning(None, "My Plugin", "qgis-sdk not installed and auto-install failed.\n\nPlease install manually:\npip install qgis-sdk\nor\nconda install -c conda-forge qgis-sdk")
        except Exception:
            print("qgis-sdk not installed")
        return None
else:
    from qgis_sdk import plugin, toolbar, action

    @plugin(name="My Plugin", version="0.1.0", description="...", author="Me", qgis_min_version="3.28")
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
qgis-plugin vendor --output my_plugin/vendor
qgis-plugin vendor --output my_plugin/extlibs --wheel
qgis-plugin package --bundle
qgis-plugin package --bundle --offline
qgis-plugin bootstrap --output my_plugin/bootstrap.py
```

**QGIS Plugin Repository — metadata.txt:**

```ini
[general]
name=My Plugin
...
plugin_dependencies=qgis_sdk_plugin
qgis_sdk_min_version=0.1.0
qgis_sdk_auto_install=True
```

**Flow for user who installs zip:**
1. User downloads `my_plugin.zip` from QGIS Plugin Repository.
2. QGIS Plugin Manager extracts to `.../python/plugins/my_plugin/`.
3. QGIS calls `classFactory(iface)`:
   - `bootstrap` checks `extlibs/qgis_sdk` → not found
   - Checks `vendor/qgis_sdk` → if `--bundle` was used, found → import → works → no dialog
   - If not bundled, shows dialog "qgis-sdk required, install now?"
   - If Yes: pip install to `extlibs` (user-local, no admin), add to path, import, continue
4. Plugin registers itself via declarative decorators, toolbar appears.

---

## 7. Migration Steps (Incremental, no big bang) — Updated with Bootstrap + Bun + QGIS API

### Phase 1 — Package split + Bootstrap + Bun (1-2 days)
- [ ] Create `packages-py/` and `packages-bun/` dirs
- [ ] Move `packages/qgis-sdk` → `packages-py/qgis-sdk`, clean
- [ ] Move `packages/qgis-sdk-bridge` → `packages-bun/qgis-sdk-bridge`, delete stray py files, fix `package.json` exports to use bun
- [ ] Move `packages/qgis-node` → `packages-bun/qgis-rs-bun`, `packages/qgis-rs` → `packages-py/qgis-rs`
- [ ] Init root `package.json` with bun workspaces, add `bun.lockb`
- [ ] Update root `Cargo.toml` workspace: `members = ["packages-rs/*", "packages-py/qgis-sdk"]`
- [ ] Update `pyproject.toml` maturin manifest paths
- [ ] Update CI: test `packages-py/*` with `pytest`, `packages-bun/*` with `bun test` (oven/bun image)
- [ ] Create `packages-py/qgis-sdk/src/qgis_sdk/bootstrap.py` + `installer.py`
- [ ] Update `scaffold.py` to generate `bootstrap.py` + `__init__.py` with self-registering logic + `extlibs/` gitignore
- [ ] Verify `pip install -e packages-py/qgis-sdk` and `bun install` in bridge still work

### Phase 2 — Tests mimic src (1 day)
- [ ] For each `src/qgis_sdk/*.py`, create `tests/qgis_sdk/<module>/test_*.py`
- [ ] Move existing `tests/test_network.py` → `tests/qgis_sdk/network/test_manager.py` + `test_session.py` etc
- [ ] Same for `test_tasks.py` → `tests/qgis_sdk/tasks/test_task.py`, `test_celery_api.py`
- [ ] Add `tests/qgis_sdk/bridge/test_description.py`, `test_window.py`, `test_qgis_api.py`
- [ ] For bun: `packages-bun/qgis-sdk-bridge/tests/bridge/test_qgis.test.ts` etc using `bun:test`
- [ ] Update `pyproject.toml` `testpaths = ["tests"]`
- [ ] Ensure `pytest` and `bun test` both find mirrored structure

### Phase 3 — Bridge description loader + QGIS API (3-4 days)
- [ ] Create `packages-py/qgis-sdk/src/qgis_sdk/bridge/description.py`
- [ ] Create `bridge/decorators.py` with `@bridge`, `@method`, `@signal`
- [ ] Create `bridge/qgis_api/` package with layers, project, message, tasks, network, iface, settings, processing modules
- [ ] Create `bridge/qgis_api.py` aggregator `QgisApi` class that composes sub-APIs, auto-registers signals
- [ ] Create `bridge/runtime.py` with `BridgeRuntime` that registers both user bridge and `QgisApi` as "qgis" QWebChannel object, injects `window.__QGIS_BRIDGE_DESCRIPTION__` + `window.__QGIS_API_DESCRIPTION__`
- [ ] Create `bridge/window.py` with `BridgeWindow` (EventTarget-like) for Python side
- [ ] In `packages-bun/qgis-sdk-bridge/src/description.ts`: `loadDescription()`, `createBridgeFromDescription()`
- [ ] In `window.ts`: implement `QgisBridge extends EventTarget` with `CONNECTING/OPEN/CLOSED`, `onopen/onmessage/onerror/onclose`, `send()`, `close()`, `addEventListener`, `call()`, Proxy
- [ ] In `qgis.ts` + `qgis/*.ts`: implement high-level `QgisAPI` class with `layers`, `project`, `message`, `tasks`, `network`, `iface`, `settings`, `processing` — typed, EventTarget, using raw QWebChannel "qgis" object
- [ ] Implement `createQgisBridge()` factory that returns `{bridge, qgis}` and sets `window.qgis = qgis`
- [ ] Update `loader.ts` to try `window.__QGIS_BRIDGE_DESCRIPTION__` first, then QWebChannel, and also load QGIS API
- [ ] CLI: add `qgis-plugin bridge describe --bridge X --output bridge.json`
- [ ] Keep `generate` as optional for TS types, but not required
- [ ] Update scaffold to generate `web/bridge.json` not `bridge.d.ts` by default, and JS uses `createQgisBridge()` without import, example shows `qgis.layers.addVector` etc

### Phase 4 — Declarative decorator API (3-4 days)
- [ ] Create `qgis_sdk/plugin/registry.py` global registry
- [ ] Create `qgis_sdk/plugin/decorators.py` with `@plugin(permissions=[...])`, `@toolbar`, `@action`, `@menu`, `@setting`
- [ ] Refactor `plugin.py` to use registry: `Plugin` class becomes thin wrapper, `classFactory` generated from registry, permissions passed to `QgisApi`
- [ ] Update `algorithm/decorators.py` to use `@algorithm` + `@param` declarative
- [ ] Update `network/decorators.py` with `@with_auth`, `@session`
- [ ] Update `tasks/decorators.py` already celery-like, but ensure `@task` works without class and is discoverable by `qgis.tasks.run`
- [ ] Update `bridge/decorators.py` as above
- [ ] Update `scaffold.py` to generate new declarative examples with `enable_qgis_api=True` and `qgis.*` usage in web
- [ ] Ensure old class-based API still works via shim (deprecation warning)

### Phase 5 — Bootstrap & Vendor CLI (1-2 days)
- [ ] Implement `qgis-plugin vendor --output my_plugin/vendor` — copies pure-py `qgis_sdk` into vendor
- [ ] Implement `qgis-plugin vendor --output my_plugin/extlibs --wheel` — copies wheel into `wheels/`
- [ ] Implement `qgis-plugin package --bundle` — vendor + package
- [ ] Implement `qgis-plugin bootstrap --output my_plugin/bootstrap.py`
- [ ] Test in clean QGIS profile without qgis-sdk installed: install zip, trigger auto-install dialog, verify toolbar appears
- [ ] Test offline: zip with `wheels/` and `vendor/`, no internet, no pip
- [ ] Test webview with `qgis` API: bun build web, load in QGIS, test `qgis.layers.addVector` etc from JS console

### Phase 6 — Docs & Examples (1 day)
- [ ] Update `apps/docs/src/content/docs/reference/bridge.mdx` to show description loader + window-like API + `qgis` global
- [ ] New doc `reference/qgis-api.mdx` documenting `qgis.layers`, `qgis.project`, `qgis.message`, `qgis.tasks`, `qgis.network`, `qgis.iface`, `qgis.settings`, `qgis.processing` with examples
- [ ] Update `reference/network.mdx` to show requests-like + Session + `qgis.network.fetch`
- [ ] Update `reference/tasks.mdx` to show celery-like + `qgis.tasks.run` from JS
- [ ] Add `guides/declarative-api.mdx` showing all decorators
- [ ] Add `guides/bridge-window-api.mdx` showing EventSource/WebSocket-like
- [ ] Add `guides/qgis-web-api.mdx` showing complete QGIS API from JS, with React/Vue/Svelte examples using bun
- [ ] Add `guides/plugin-distribution.mdx` showing bundle, bootstrap, auto-install, offline wheel, `plugin_dependencies`
- [ ] Add `guides/bun-workflow.mdx` showing bun install, bun test, bun build, bun build --compile for CLI
- [ ] Update `getting-started/python-sdk.mdx` with new layout and `ensure_qgis_sdk()` pattern and `enable_qgis_api`
- [ ] Update `getting-started/typescript.mdx` to use bun: `bun install @qgis-sdk/bridge`, `bunx --bun vite dev`, etc

---

## 8. Example Final Plugin (Declarative + Self-Installing + QGIS Web API via Bun)

```python
# my_plugin/__init__.py — self-bootstrapping + declarative + QGIS API enabled
from qgis_sdk import plugin, toolbar, action, task, bridge, method, signal, setting

@plugin(
    name="My Plugin",
    version="0.1.0",
    description="Does useful things declaratively, with JS QGIS API",
    author="Me",
    email="me@example.com",
    qgis_min_version="3.28",
    category="Vector",
    permissions=["layers", "project", "tasks", "network", "message", "settings"]
)
class MyPlugin:
    @setting(default=10.0, persist=True)
    def distance(self): return 10.0

    @toolbar("My Toolbar")
    @action(tooltip="Run buffer", icon="icons/buffer.svg")
    def run_buffer(self, iface, distance: float):
        session = __import__("qgis_sdk.network").network.Session(auth_cfg="my_auth")
        resp = session.get("https://example.com/api", params={"distance": distance})
        resp.raise_for_status()
        result = self.buffer_task.delay(distance)
        iface.messageBar().pushMessage(f"Task {result.id} started, state={result.state}")

    @task("Buffer task", bind=True, can_cancel=True)
    def buffer_task(self, distance: float):
        self.set_progress(0)
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

    @toolbar("My Toolbar")
    @action(tooltip="Open webview with full QGIS API")
    def open_webview(self, iface):
        from qgis_sdk.ui import WebView
        from qgis.PyQt.QtCore import QUrl
        import pathlib
        # WebView auto-injects qgis API + user bridge + qwebchannel.js
        webview = WebView(
            bridge=self.Bridge(),
            enable_qgis_api=True,
            iface=iface,
            permissions=self._qgis_sdk_metadata.get("permissions")
        )
        html_path = pathlib.Path(__file__).parent / "web" / "dist" / "index.html"  # built with bun build
        webview.load(QUrl.fromLocalFile(str(html_path)))
        webview.show()

def classFactory(iface):
    return MyPlugin(iface)
```

```typescript
// web/src/app.ts — no codegen needed, windows-like + complete qgis API, built with bun
// bun install @qgis-sdk/bridge
// bun build src/app.ts --outdir dist --target browser

import { createQgisBridge, QgisBridge } from '@qgis-sdk/bridge';

// createQgisBridge loads both user bridge and built-in qgis global
const { bridge, qgis } = await createQgisBridge();

// ---- qgis global — no custom Python bridge needed for these ----

// Show message in QGIS messageBar from JS
await qgis.message.info("My Plugin", "Webview ready!", 3);
qgis.messageBar.pushMessage("Hello", "From JS", 0, 5);

// Layers
const layers = await qgis.layers.list();
console.log("Layers", layers);

const roads = await qgis.layers.addVector("/data/roads.shp", "Roads", "ogr");
console.log("Added", roads.id);
await qgis.layers.zoomTo(roads.id);

// Listen to layer added/removed via EventTarget
qgis.layers.onAdded((e) => console.log("layer added", e.detail));
qgis.addEventListener("layer_added", (e: any) => console.log("added", e.detail));

// Project
await qgis.project.setCrs("EPSG:4326");
console.log(await qgis.project.info());

// Tasks — trigger Python @task from JS
const task = await qgis.tasks.run("buffer_task", {distance: 10});
task.onProgress(p => {
  document.getElementById("progress")!.textContent = `${p}%`;
});
task.onFinished(result => {
  console.log("Task finished", result);
  qgis.message.success("Task", `Done: ${JSON.stringify(result)}`);
});

// Network via QGIS (uses QGIS proxy, auth, no CORS issues)
const resp = await qgis.network.fetch("https://example.com/api/secure", {authCfg: "my_auth"});
const data = await resp.json();
console.log(data);

// Settings
await qgis.settings.set("last_search", "roads");
console.log(await qgis.settings.get("last_search"));

// ---- custom bridge still works alongside qgis global ----
bridge.addEventListener("open", () => console.log("bridge open, state:", bridge.readyState));
bridge.addEventListener("layer_changed", (e) => console.log("layer changed", e.detail));

const layer = await bridge.get_layer("my_layer"); // from user Bridge class
await bridge.call("log", "hello from JS");

bridge.send({action: "buffer"});
console.log(bridge.readyState === QgisBridge.OPEN);

// React example (with bun)
// import { useQgis } from '@qgis-sdk/bridge/react';
// const { qgis, ready } = useQgis();
// useEffect(() => { if (!ready) return; qgis.layers.list().then(setLayers); }, [ready]);

// Vue example
// const { qgis, ready } = useQgis();
// watch(ready, (r) => { if (r) qgis.layers.list().then(...) });

// Svelte
// import { qgisStore } from '@qgis-sdk/bridge/svelte';
// $qgisStore.layers.list().then(...)
```

```json
// web/package.json — bun
{
  "name": "my-plugin-web",
  "type": "module",
  "scripts": {
    "dev": "bun --bun vite",
    "build": "bun build src/app.ts --outdir dist --target browser --minify",
    "test": "bun test"
  },
  "dependencies": {
    "@qgis-sdk/bridge": "workspace:*"
  },
  "devDependencies": {
    "vite": "^5.0.0"
  }
}
```

```toml
# Root package.json (bun workspaces)
{
  "workspaces": ["packages-bun/*", "apps/*"],
  "scripts": {
    "build": "bun run --filter '*' build",
    "test": "bun test",
    "dev": "bun --bun astro dev --filter docs",
    "lint": "bunx biome check ."
  },
  "packageManager": "bun@1.2.0"
}
```

---

## 9. Risks & Mitigations

- **Breaking change for existing plugins:** Keep old `Plugin` base class as shim that delegates to registry, with deprecation warning. Scaffold generates new API but old still works.
- **Rust workspace split:** Keep `Cargo.toml` at root with `members = ["packages-rs/*", "packages-py/qgis-sdk"]` so `maturin develop` still works. For `packages-bun`, use `napi-rs` or keep JS fallback.
- **Bridge description JSON injection:** QWebChannel `runJavaScript` may not be ready immediately — inject via `setHtml` with `<script>window.__QGIS_BRIDGE_DESCRIPTION__ = ...</script>` before loading page.
- **Tests mirroring src:** Need to update `pyproject.toml` and ensure CI caches. Use `pytest --import-mode=importlib` to avoid import conflicts.
- **QGIS API security:** JS can do powerful things (add/remove layers, run tasks, network). Mitigate via `permissions` in `@plugin(permissions=[...])` — if not granted, method returns error. Also QGIS trust: webview content is bundled by plugin author (local files), not remote untrusted URL, so safe. For remote URLs, disable qgis API or require explicit `enable_qgis_api=True` + permission.
- **Bun adoption:** QGIS devs may not have bun. Provide fallback: `npm install` still works because `package.json` is compatible, but docs recommend bun. CI tests both `bun install` and `npm install` for compatibility. `qgis-plugin` CLI still works with node if bun not found.
- **QWebChannel async:** QWebChannel methods are async, but we wrap in Promise and EventTarget. Need robust `_connect()` that retries if `qt` not yet injected. Use `window.qt` polling.

---

## 10. Deliverables Checklist

- [ ] `packages-py/` and `packages-bun/` layout (bun workspaces, bun.lockb)
- [ ] `qgis-bridge` Python package with description loader (no codegen required)
- [ ] `QgisBridge extends EventTarget` with `readyState`, `onopen/onmessage/onerror/onclose`, `send()`, `close()`, `addEventListener`, `call()`, Proxy for methods — feels like `WebSocket`/`EventSource`/`window` (bun-built)
- [ ] **Complete QGIS Web API**: `QgisApi` Python class + `QgisAPI` TS class with `qgis.layers`, `qgis.project`, `qgis.message/messageBar`, `qgis.tasks`, `qgis.network`, `qgis.iface`, `qgis.settings`, `qgis.processing` — auto-registered as `qgis` QWebChannel object, available as `window.qgis` in JS, no custom bridge needed for common ops
- [ ] `createQgisBridge()` factory returning `{bridge, qgis}`, sets `window.qgis`
- [ ] `tests/` mirrors `src/` for each package (pytest + bun:test)
- [ ] `qgis-sdk` declarative API via decorators: `@plugin(permissions=[...])`, `@toolbar`, `@action`, `@task`, `@bridge`, `@method`, `@signal`, `@setting`, `@algorithm`, `@param`
- [ ] Scaffold generates new declarative examples with `enable_qgis_api=True` and web using `qgis.*` + bun build
- [ ] Self-installing runtime: `bootstrap.py`, `installer.py`, `vendor/package --bundle`, offline wheel
- [ ] Docs updated: `guides/declarative-api.mdx`, `guides/bridge-window-api.mdx`, `guides/qgis-web-api.mdx`, `guides/bun-workflow.mdx`, `guides/plugin-distribution.mdx`, `reference/qgis-api.mdx`
- [ ] Root `package.json` uses bun workspaces, `bun.lockb` committed, CI uses `oven/bun`
- [ ] All 112+ tests passing, plus new bridge description + qgis API tests (py + bun)
- [ ] Example web app built with `bun build`, uses `qgis.layers.addVector`, `qgis.tasks.run`, `qgis.network.fetch`, `qgis.message.info` from JS without custom bridge boilerplate
