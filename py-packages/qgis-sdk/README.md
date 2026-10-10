# qgis-sdk

Python SDK for building QGIS plugins on top of PyQGIS — **with Rust-native CLI, UI dialogs, and WebEngine support**.

It is a **pixi workspace package** and **maturin Python package**: the `[package]` section lives in [`pixi.toml`](./pixi.toml), Rust crate in [`Cargo.toml`](./Cargo.toml), and Python packaging metadata in [`pyproject.toml`](./pyproject.toml).

```
qgis-sdk = better PyQGIS + declarative plugin/algorithm/UI definitions + Rust CLI at native speed
```

- **pip**: `pip install qgis-sdk` → `import qgis_sdk` + `qgis-sdk` binary on PATH (Rust)
- **conda**: `conda install -c conda-forge qgis-sdk` → same, with QGIS backend
- **API**: `from qgis_sdk import Plugin, Algorithm, Dialog, WebDialog` — Pythonic, type-hinted, testable without QGIS
- **CLI**: `qgis-sdk` (Rust binary) + `qgis-sdk` Python console script — scaffold, build, test, package at native speed
- **UI**: `qgis_sdk.ui` — Qt Designer `.ui` + `uic.loadUiType` + `WA_DeleteOnClose` + `QSettings` + `QWebEngineView` + `QWebChannel` bridge

## What it gives you

| Piece | Purpose |
|-------|---------|
| `Plugin`, `@action`, `@toolbar`, `@menu` | Declare a plugin as a class; get the toolbar buttons, menu entries, and `initGui`/`unload` lifecycle for free. |
| `render_metadata()` / `write_metadata()` | `metadata.txt` generated from the class attributes, so it cannot drift. |
| `Algorithm`, `parameter`, `output` | Declarative Processing parameters and outputs. |
| `Dialog`, `field`, `layout`, `Button`, `@dialog` | Declarative dialogs via PyQt — testable without QGIS, with `QSettings` persistence. |
| `WebDialog`, `@web_bridge` | QWebEngineView + HTML/CSS/JS + QWebChannel bridge (Python ↔ JS via `pyqtSlot` + `runJavaScript`). |
| `generate_ts_bridge()`, `generate_package()` | Generate TypeScript types from Python bridge classes → `bridge.d.ts` with Promise+callback overloads, for `@archont561/qgis-sdk`. |
| `@archont561/qgis-sdk` (npm) | Typed bridge runtime: auto-injects `qrc:///qtwebchannel/qwebchannel.js`, `createBridge<T>()` Promise API, React `useQgisBridge`, Vue composable, Web Components `<qgis-bridge>`. |
| `qgis_sdk.testing` | Pytest fixtures + fakes, one module per concern: `FakeIface`, `FakeDialog`, `FakeWebView`, `BridgeHarness`, `FakeNetworkTransport`, the `PENDING/RUNNING/SUCCESS/FAILURE/CANCELED` `FakeTaskManager`, `Call`/`CallLog`, `mock_features/source/context`, and Hypothesis strategies in `qgis_sdk.testing.strategies`. Discoverable via `pytest_plugins = ["qgis_sdk.testing"]`. |
| `qgis_core()` / `require_qgis()` | Lazy PyQGIS access with an actionable error when the bindings are missing. |

## Using it

```python
from qgis_sdk import Plugin, action, toolbar, menu

class MyPlugin(Plugin):
    name = "My Plugin"
    version = "0.1.0"
    description = "Does useful things"
    author = "Your Name"
    email = "you@example.com"
    qgis_min_version = "3.28"
    category = "Vector"

    @toolbar("My Toolbar")
    @action(tooltip="Run my tool", icon="icons/tool.svg")
    def run_tool(self, iface):
        layer = iface.activeLayer()
        print(layer.name(), layer.featureCount())

    @menu("Plugins", "My Plugin", "Settings")
    def open_settings(self, iface):
        ...
```

```python
from qgis_sdk import Algorithm, output, parameter

class BufferAdvanced(Algorithm):
    id = "my_plugin:buffer_advanced"
    name = "Advanced Buffer"
    group = "Vector geometry"

    input_layer = parameter.source("Input layer")
    distance = parameter.distance("Buffer distance", default=10.0)
    dissolve = parameter.boolean("Dissolve results", default=False)

    output_layer = output.sink("Buffered")

    def process(self, context):
        distance = context.get("distance")
        context.set_progress(1.0)
        return {self.output_layer.name: distance}
```

## Installation

### From PyPI (pip) — Rust-native CLI + Python API

```bash
pip install qgis-sdk
```

What you get:

- `qgis_sdk` Python module (Plugin, Algorithm, metadata, plus Rust `_core` for native speed)
- `qgis-sdk` executable (Rust binary, built by maturin)
- `qgis-sdk` executable (alias)
- `qgis-sdk` and `qgis-sdk` console scripts (`python -m qgis_sdk.cli`)

Pre-built wheels for Linux x86_64 and Linux arm64. If no wheel matches, pip builds from source via maturin (requires Rust ≥1.96).

### From conda-forge

```bash
conda install -c conda-forge qgis-sdk
# or
pixi add qgis-sdk
```

The conda-forge package depends on `qgis >=3.44.9`, so PyQGIS works out of the box, plus `qgis-sdk` binary in `$CONDA_PREFIX/bin`.

### From source (development)

```bash
git clone https://github.com/Archont561/qgis-rust
cd qgis-rs

# Python dev with maturin (Rust-native)
pip install maturin
(cd py-packages/qgis-sdk && maturin develop)

# Or via pixi (conda env with QGIS)
pixi install -e default
pixi run -e default python -m pytest py-packages/qgis-sdk/tests -v
pixi run -e default qgis-sdk --help

# Test without Rust (pure Python fallback)
python -m pytest py-packages/qgis-sdk/tests -q
```

## CLI — Rust-native, pip-installable

```bash
# Scaffold a new plugin (Rust does file creation at native speed)
qgis-sdk new my_plugin --type processing --rust
qgis-sdk new my_plugin --web --author "Your Name" --email "you@example.com"
qgis-sdk new my_plugin --web --framework react # react, vue, webcomponents, vanilla
qgis-sdk new my_plugin --no-ui  # skip UI scaffolding

# Typed bridge generation (Python -> TS)
qgis-sdk bridge generate --bridge my_plugin.dialogs.web_dialog:Bridge --output web/bridge.d.ts
qgis-sdk bridge generate --bridge my_plugin.dialogs.web_dialog:Bridge --output web/ --package --framework react

# Validate structure
qgis-sdk validate
qgis-sdk validate ./my_plugin --json

# Build, test, install
qgis-sdk build
qgis-sdk test
qgis-sdk install
qgis-sdk dev --rust --launch

# Package for QGIS Plugin Repository (includes ui/*.ui, web/*.html, web/*.d.ts, icons/*)
qgis-sdk package -o dist/
qgis-sdk publish --zip dist/my_plugin-0.1.0.zip --dry-run

# Rust acceleration
qgis-sdk rust init
qgis-sdk rust build --release

# UI helpers
qgis-sdk ui add-dialog ./my_plugin --name custom_dialog
qgis-sdk ui add-web ./my_plugin

# Info and version
qgis-sdk info
qgis-sdk info --json
qgis-sdk version

# Via Python module (same speed — uses Rust extension directly)
python -m qgis_sdk.cli new my_plugin --web --framework react
python -m qgis_sdk.cli bridge generate --bridge my_plugin.dialogs.web_dialog:Bridge --output web/bridge.d.ts
python -m qgis_sdk.cli validate
```

## UI — Dialogs via PyQt and WebEngine

### Qt Designer .ui pattern (recommended)

```python
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import QSettings, Qt
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui", "main_dialog.ui"))

class MainDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WA_DeleteOnClose)  # avoid QGIS crashes
        self._restore_settings()

    def _restore_settings(self):
        s = QSettings()
        self.name_field.setText(s.value("my_plugin/main_dialog/name", "", type=str))

    def get_values(self):
        return {
            "input_layer": self.input_layer.currentLayer(),
            "threshold": self.threshold.value(),
        }
```

### Declarative fallback (testable without QGIS)

```python
from qgis_sdk.ui import Dialog, field, layout, Button, dialog

@dialog(title="Main Dialog", persist=True)
def make_dialog():
    return [
        field.layer("input_layer", label="Input layer"),
        field.spin("threshold", label="Threshold", default=0.5),
        field.text("name", label="Name"),
    ]

dlg = make_dialog()
if dlg.exec() == Dialog.Accepted:
    print(dlg.get("input_layer"))
```

### WebEngine + QWebChannel (HTML/CSS/JS)

```python
from qgis_sdk.ui import WebDialog, web_bridge
from pathlib import Path

dlg = WebDialog.from_file(Path("web/map.html"), title="Map View", width=900, height=700)

@web_bridge(dlg)
class Bridge:
    def get_layer(self):
        return {"name": "buildings", "count": 100}

dlg.exec()
```

```html
<!-- web/map.html -->
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
new QWebChannel(qt.webChannelTransport, function(channel) {
    bridge = channel.objects.bridge;
    bridge.get_layer(function(data) {
        console.log(data);
    });
});
function updateFromPython(data) {
    console.log("From Python:", data);
}
</script>
```

Python → JS: `dlg.run_js("updateFromPython({center: [51.5, -0.09]})")` or `runJavaScript("window.qgisBridge.onMessage(...)")` → `CustomEvent('qgis-message')`  
JS → Python: `@pyqtSlot(result=str)` + `QWebChannel.registerObject("bridge", bridge_obj)` → `await bridge.get_layer()` via `@archont561/qgis-sdk`

### Typed bridge with @archont561/qgis-sdk (npm)

```bash
npm install @archont561/qgis-sdk
qgis-sdk bridge generate --bridge my_plugin.dialogs.web_dialog:Bridge --output web/bridge.d.ts
```

```typescript
import { createBridge } from '@archont561/qgis-sdk';
import type { Bridge } from './web/bridge.d.ts';

const bridge = await createBridge<Bridge>(); // auto-injects qrc:///qtwebchannel/qwebchannel.js
const layer = await bridge.get_layer(); // typed!

// React
import { useQgisBridge } from '@archont561/qgis-sdk/react';
const { bridge, ready } = useQgisBridge<Bridge>();

// Vue
import { useQgisBridge } from '@archont561/qgis-sdk/vue';
const { bridge, ready } = useQgisBridge<Bridge>();

// Web Components
import '@archont561/qgis-sdk/webcomponents';
<qgis-bridge object-name="bridge"></qgis-bridge>
```

See [Typed Bridge Guide](https://archont561.github.io/qgis-rust/guides/typed-bridge/) and [Web Frameworks Guide](https://archont561.github.io/qgis-rust/guides/web-frameworks/).

### Testing fixtures (no QGIS needed)

```python
# tests/conftest.py
pytest_plugins = ["qgis_sdk.testing"]

def test_toolbar(fake_iface, fake_action_factory):
    from my_plugin import MyPlugin
    MyPlugin.action_factory = staticmethod(fake_action_factory)
    plugin = MyPlugin(fake_iface)
    plugin.init_gui()
    assert len(fake_iface.toolbar_icons) == 1

def test_bridge(fake_bridge):
    assert fake_bridge.get_layer()["name"] == "test_layer"
```

Deterministic by construction — nothing sleeps, nothing opens a socket, and
nothing answers a question the test did not script:

```python
def test_a_retry_gives_up_after_the_second_failure(fake_network_transport):
    fake_network_transport.reply_sequence("GET", "https://example.test/api", [
        FakeResponse(status_code=503),
        FakeResponse(status_code=200, json_data={"ok": True}),
    ])
    ...  # an unscripted URL raises NoScriptedReply instead of inventing a 200

def test_the_task_runs_when_i_say_so(manual_task_manager):
    task = manual_task_manager.submit(work)
    assert task.state == "PENDING"
    manual_task_manager.run_next()
    assert task.state == "SUCCESS"

def test_the_bridge_refuses_an_unknown_method(bridge_harness_factory):
    harness = bridge_harness_factory(descriptions={"qgis": manifest})
    answer = harness.invoke({"bridge_version": 1, "request_id": "req-1",
                             "target": "qgis", "method": "layers.teleport", "args": {}})
    assert answer["error"]["kind"] == "unknown_method"
```

Fakes: `FakeIface`, `FakeAction`, `FakeDialog`, `FakeWebView`, `FakeBridge`,
`BridgeHarness`, `FakeNetworkTransport`, `FakeTaskManager`, `Call`/`CallLog`,
`mock_features()`, `mock_source()`, plus Hypothesis strategies in
`qgis_sdk.testing.strategies`. Markers `qgis`, `qt`, `webengine` and
`pure_python` skip a test whose layer is missing instead of handing it a fake.
See [Testing Fixtures Guide](https://archont561.github.io/qgis-rust/guides/testing-fixtures/).

Skipping is the right default and a poor proof. To assert that a layer really
works, run its gate — it narrows the suite to that layer and **fails** if the
layer is missing:

```bash
bun run test            # everything, skipping what this machine cannot reach
bun run test:pure       # no Qt, no QGIS, no WebEngine — the fakes and the harness
bun run test:qt         # real widgets, offscreen
bun run test:qgis       # a real QgsApplication, built and shut down by the suite
bun run test:webengine  # optional, and deliberately not on the default path
```

## Development

From the repository root:

```bash
bun x turbo run test --filter=qgis-sdk              # pytest (35 tests, no QGIS needed)
cd py-packages/qgis-sdk && bun run doctor && cd ../..  # prove `import qgis.core` resolves
```

Or without pixi, if Python and the package are already installed:

```bash
cd py-packages/qgis-sdk
python -m pytest -q
# With Rust
maturin develop && python -m pytest -q
```

### Testing without QGIS

Nothing in `qgis_sdk` imports `qgis` at module scope — `qgis_sdk.runtime` does
it lazily. That is deliberate: the test-suite injects a fake interface and a
fake action factory, so plugin and algorithm logic is testable on a machine
with no QGIS at all.

```python
class FakeIface:
    def addToolBarIcon(self, widget): ...
    def addPluginToMenu(self, path, widget): ...

class MyTestPlugin(MyPlugin):
    action_factory = staticmethod(lambda spec, cb: FakeAction(spec, cb))
```

## Import resolution

`import qgis.core` works because the conda-forge `qgis` package ships an
activation script that puts the bindings on `PYTHONPATH`:

```
$CONDA_PREFIX/share/qgis/python
$CONDA_PREFIX/share/qgis/python/plugins
```

and sets `QGIS_PREFIX_PATH=$CONDA_PREFIX`. Pixi runs those scripts for
`pixi run` and `pixi shell`, and the `sdk` feature repeats the same variables in
`[feature.sdk.activation.env]` so the paths are explicit. `qgis_sdk.runtime`
reports exactly this when an import fails.

## Status

The declarative layers (`Plugin`, decorators, `metadata.txt`, `Algorithm`
parameters) are implemented and unit-tested. The QGIS bridges —
`qgis_sdk.qt.make_action` and `qgis_sdk.processing_bridge.build_algorithm` —
are written against PyQGIS but need a QGIS environment to exercise.

## Vendored bridge bundle

WebEngine scaffolds (`--web`) copy a pinned browser bundle of `@archont561/qgis-sdk`
into `web/qgis-sdk.js`. Plain scaffolds do not include it.

The bundle lives in `src/qgis_sdk/assets/bridge/` together with `manifest.json`, which
pins the package version and the bundle's sha256. To refresh it:

```sh
cd ts-packages/qgis-sdk && bun run build
python py-packages/qgis-sdk/scripts/vendor_bridge.py
```

On a WebEngine page the bundle publishes the QGIS API as globals, so a plain script
needs no bundler: `window.qgis` (layers, project, message, tasks, network, iface, settings),
`window.qgisBridge`, and `window.qgisReady` (a promise for `window.qgis`). It also publishes
`window.qgisChannel(transport, cb)`, which the scaffolded pages use. Open the page's
QWebChannel through it rather than with `new QWebChannel(...)`, because a second channel on
one transport takes over the first one's replies. Outside WebEngine nothing is published.

`tests/test_bridge_vendor.py` fails if the vendored file and manifest drift apart, or if
the manifest version differs from the TypeScript package.
