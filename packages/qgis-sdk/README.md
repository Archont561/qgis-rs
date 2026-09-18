# qgis-sdk

Python SDK for building QGIS plugins on top of PyQGIS. It is a **pixi workspace
package**: the `[package]` section lives in [`pixi.toml`](./pixi.toml) and the
Python packaging metadata in [`pyproject.toml`](./pyproject.toml).

```
qgis-sdk = better PyQGIS + declarative plugin/algorithm definitions
```

## What it gives you

| Piece | Purpose |
|-------|---------|
| `Plugin`, `@action`, `@toolbar`, `@menu` | Declare a plugin as a class; get the toolbar buttons, menu entries, and `initGui`/`unload` lifecycle for free. |
| `render_metadata()` / `write_metadata()` | `metadata.txt` generated from the class attributes, so it cannot drift. |
| `Algorithm`, `parameter`, `output` | Declarative Processing parameters and outputs. |
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

## Development

From the repository root:

```bash
pixi run -e sdk sdk-test      # pytest
pixi run -e sdk sdk-doctor    # prove `import qgis.core` resolves
```

Or without pixi, if Python and the package are already installed:

```bash
cd packages/qgis-sdk
python -m pytest -q
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
