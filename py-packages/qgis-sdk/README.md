# qgis-sdk

Python SDK for building QGIS plugins on top of PyQGIS — **with Rust-native CLI, UI dialogs, and WebEngine support**.

It is a **pixi workspace package** and **maturin Python package**: the `[package]` section lives in [`pixi.toml`](./pixi.toml), Rust crate in [`Cargo.toml`](./Cargo.toml), and Python packaging metadata in [`pyproject.toml`](./pyproject.toml).

```
qgis-sdk = better PyQGIS + declarative plugin/algorithm/UI definitions + Rust CLI at native speed
```

- **pip**: `pip install qgis-sdk` → `import qgis_sdk` + `qgis-plugin` binary on PATH (Rust)
- **conda**: `conda install -c conda-forge qgis-sdk` → same, with QGIS backend
- **API**: `from qgis_sdk import Plugin, Algorithm, Dialog, WebDialog` — Pythonic, type-hinted, testable without QGIS
- **CLI**: `qgis-plugin` (Rust binary) + `qgis-plugin` Python console script — scaffold, build, test, package at native speed
- **UI**: `qgis_sdk.ui` — Qt Designer `.ui` + `uic.loadUiType` + `WA_DeleteOnClose` + `QSettings` + `QWebEngineView` + `QWebChannel` bridge

## What it gives you

| Piece | Purpose |
|-------|---------|
| `Plugin`, `@action`, `@toolbar`, `@menu` | Declare a plugin as a class; get the toolbar buttons, menu entries, and `initGui`/`unload` lifecycle for free. |
| `render_metadata()` / `write_metadata()` | `metadata.txt` generated from the class attributes, so it cannot drift. |
| `Algorithm`, `parameter`, `output` | Declarative Processing parameters and outputs. |
| `Dialog`, `field`, `layout`, `Button`, `@dialog` | Declarative dialogs via PyQt — testable without QGIS, with `QSettings` persistence. |
| `WebDialog`, `@web_bridge` | QWebEngineView + HTML/CSS/JS + QWebChannel bridge (Python ↔ JS via `pyqtSlot` + `runJavaScript`). |
| `generate_ts_bridge()`, `generate_package()` | Generate TypeScript types from Python bridge classes → `bridge.d.ts` with Promise+callback overloads, for `@qgis-sdk/bridge`. |
| `@qgis-sdk/bridge` (npm) | Typed bridge runtime: auto-injects `qrc:///qtwebchannel/qwebchannel.js`, `createBridge<T>()` Promise API, React `useQgisBridge`, Vue composable, Web Components `<qgis-bridge>`. |
| `qgis_sdk.testing` | Pytest fixtures + fakes: `FakeIface`, `FakeDialog`, `FakeWebView`, `FakeBridge`, `mock_features/source/context`, `fake_iface`, `fake_bridge`, etc. Discoverable via `pytest_plugins = ["qgis_sdk.testing"]`. |
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
- `qgis-plugin` executable (Rust binary, built by maturin)
- `qgis-sdk` executable (alias)
- `qgis-plugin` and `qgis-sdk` console scripts (`python -m qgis_sdk.cli`)

Pre-built wheels for Linux x86_64, macOS arm64/x86_64, Windows x86_64. If no wheel matches, pip builds from source via maturin (requires Rust ≥1.96).

### From conda-forge

```bash
conda install -c conda-forge qgis-sdk
# or
pixi add qgis-sdk
```

The conda-forge package depends on `qgis >=3.44.9`, so PyQGIS works out of the box, plus `qgis-plugin` binary in `$CONDA_PREFIX/bin`.

### From source (development)

```bash
git clone https://github.com/Archont561/qgis-rs
cd qgis-rs

# Python dev with maturin (Rust-native)
pip install maturin
(cd py-packages/qgis-sdk && maturin develop)

# Or via pixi (conda env with QGIS)
pixi install -e sdk
pixi run -e sdk python -m pytest py-packages/qgis-sdk/tests -v
pixi run -e sdk qgis-plugin --help

# Test without Rust (pure Python fallback)
python -m pytest py-packages/qgis-sdk/tests -q
```

## CLI — Rust-native, pip-installable

```bash
# Scaffold a new plugin (Rust does file creation at native speed)
qgis-plugin new my_plugin --type processing --rust
qgis-plugin new my_plugin --web --author "Your Name" --email "you@example.com"
qgis-plugin new my_plugin --web --framework react # react, vue, webcomponents, vanilla
qgis-plugin new my_plugin --no-ui  # skip UI scaffolding

# Typed bridge generation (Python -> TS)
qgis-plugin bridge generate --bridge my_plugin.dialogs.web_dialog:Bridge --output web/bridge.d.ts
qgis-plugin bridge generate --bridge my_plugin.dialogs.web_dialog:Bridge --output web/ --package --framework react

# Validate structure
qgis-plugin validate
qgis-plugin validate ./my_plugin --json

# Build, test, install
qgis-plugin build
qgis-plugin test
qgis-plugin install
qgis-plugin dev --rust --launch

# Package for QGIS Plugin Repository (includes ui/*.ui, web/*.html, web/*.d.ts, icons/*)
qgis-plugin package -o dist/
qgis-plugin publish --zip dist/my_plugin-0.1.0.zip --dry-run

# Rust acceleration
qgis-plugin rust init
qgis-plugin rust build --release

# UI helpers
qgis-plugin ui add-dialog ./my_plugin --name custom_dialog
qgis-plugin ui add-web ./my_plugin

# Info and version
qgis-plugin info
qgis-plugin info --json
qgis-plugin version

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
JS → Python: `@pyqtSlot(result=str)` + `QWebChannel.registerObject("bridge", bridge_obj)` → `await bridge.get_layer()` via `@qgis-sdk/bridge`

### Typed bridge with @qgis-sdk/bridge (npm)

```bash
npm install @qgis-sdk/bridge
qgis-plugin bridge generate --bridge my_plugin.dialogs.web_dialog:Bridge --output web/bridge.d.ts
```

```typescript
import { createBridge } from '@qgis-sdk/bridge';
import type { Bridge } from './web/bridge.d.ts';

const bridge = await createBridge<Bridge>(); // auto-injects qrc:///qtwebchannel/qwebchannel.js
const layer = await bridge.get_layer(); // typed!

// React
import { useQgisBridge } from '@qgis-sdk/bridge/react';
const { bridge, ready } = useQgisBridge<Bridge>();

// Vue
import { useQgisBridge } from '@qgis-sdk/bridge/vue';
const { bridge, ready } = useQgisBridge<Bridge>();

// Web Components
import '@qgis-sdk/bridge/webcomponents';
<qgis-bridge object-name="bridge"></qgis-bridge>
```

See [Typed Bridge Guide](https://archont561.github.io/qgis-rs/guides/typed-bridge/) and [Web Frameworks Guide](https://archont561.github.io/qgis-rs/guides/web-frameworks/).

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

Fakes: `FakeIface`, `FakeAction`, `FakeDialog`, `FakeWebView`, `FakeBridge`, `mock_features()`, `mock_source()`. See [Testing Fixtures Guide](https://archont561.github.io/qgis-rs/guides/testing-fixtures/).

## Development

From the repository root:

```bash
pixi run -e sdk sdk-test      # pytest (35 tests, no QGIS needed)
pixi run -e sdk sdk-doctor    # prove `import qgis.core` resolves
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
