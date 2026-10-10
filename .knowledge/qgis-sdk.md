---
type: concept
title: "QGIS Plugin SDK — Pure Python over PyQGIS"
description: "Python framework for building QGIS plugins with a clean API over PyQGIS. Users write Python; a typer CLI handles scaffolding, validation, testing, packaging and installation. D15 removed every Rust path from the SDK."
tags: [plugin, sdk, python, pyqgis, qgis, cli, typer, tooling]
generated: "2026-09-17T17:30:00Z"
status: draft
---

# QGIS Plugin SDK

A Python framework for building QGIS plugins — in Python, over PyQGIS.

## Philosophy

```
qgis-sdk = better PyQGIS + CLI tooling

   PyQGIS (raw)          qgis-sdk
   ─────────────         ─────────────────
   verbose               decorators + builders
   C++-ish API           Pythonic API
   no packaging          CLI: scaffold → validate → test → package → install
   bare metadata.txt     metadata from one 20-field table
   no testing story      unit tests without QGIS
```

Users write Python. The SDK provides cleaner wrappers around PyQGIS and eliminates boilerplate. Rust is not part of it: [D15](decisions/D15-qgis-sdk-cli-pure-python-typer.md) §3 as amended by TASK-57 removes every Rust path from qgis-sdk, so there is no accelerated hot path to opt into and nothing in the CLI drives `cargo`. A plugin that wants one builds and ships its own extension outside the SDK.

---

## 1. Python API — Core

### 1.1 Plugin Definition

```python
from qgis_sdk import Plugin, action, menu, toolbar

class MyPlugin(Plugin):
    """A plugin that does X, Y, and Z."""

    name = "My Plugin"
    version = "0.1.0"
    description = "Does useful things"
    author = "Your Name"
    email = "you@example.com"
    qgis_min_version = "3.28"
    category = "Vector"

    @toolbar("My Toolbar")
    @action(icon="icons/tool.svg", tooltip="Run my tool")
    def run_tool(self, iface):
        """Called when the user clicks the toolbar button."""
        layer = iface.active_layer
        iface.message(f"Active layer: {layer.name} ({layer.feature_count} features)")

    @menu("Plugins", "My Plugin", "Settings")
    def open_settings(self, iface):
        """Called when the user opens plugin settings."""
        dialog = SettingsDialog()
        dialog.exec()
```

**What the SDK generates from this:**
- `__init__.py` with `classFactory(iface)`
- `metadata.txt` from the class attributes
- Toolbar buttons and menu items from decorators
- Proper `initGui()` / `unload()` lifecycle

### 1.2 Processing Algorithm

```python
from qgis_sdk import Algorithm, parameter, output

class BufferAdvanced(Algorithm):
    """Buffer features with optional dissolve and end cap styles."""

    id = "my_plugin:buffer_advanced"
    name = "Advanced Buffer"
    group = "Vector geometry"
    description = "Buffers features with dissolve and end cap options"

    # Parameters — declarative, type-safe, generates QGIS Processing UI
    input_layer = parameter.source("Input layer", required=True)
    distance = parameter.distance("Buffer distance", default=10.0)
    dissolve = parameter.boolean("Dissolve results", default=False)
    end_cap = parameter.enum("End cap style",
        options=["Round", "Flat", "Square"],
        default="Round"
    )

    # Output
    output_layer = output.sink("Buffered")

    def process(self, context):
        """Main algorithm logic."""
        source = context.get(self.input_layer)
        dist = context.get(self.distance)
        should_dissolve = context.get(self.dissolve)
        cap = context.get(self.end_cap)

        sink = context.create_sink(
            self.output_layer,
            fields=source.fields,
            geometry_type=source.geometry_type,
        )

        for i, feature in enumerate(source.features()):
            context.set_progress(i / source.feature_count)
            if context.is_canceled:
                return

            geom = feature.geometry
            buffered = geom.buffer(dist, segments=8, end_cap_style=cap)

            out = feature.clone()
            out.geometry = buffered
            sink.add_feature(out)

        if should_dissolve:
            sink.dissolve()

        return {self.output_layer: sink}
```

### 1.3 Using the Cleaner PyQGIS Wrappers

The SDK provides Pythonic wrappers around common PyQGIS operations:

```python
from qgis_sdk import iface, project, layers, crs

# Instead of: QgsProject.instance().mapLayersByName("buildings")[0]
layer = layers.by_name("buildings")

# Instead of: iface.activeLayer()
layer = iface.active_layer

# Instead of: layer.featureCount()
count = layer.feature_count

# Instead of: QgsCoordinateReferenceSystem("EPSG:4326")
wgs84 = crs.from_epsg(4326)

# Instead of:
#   request = QgsFeatureRequest()
#   request.setFilterRect(QgsRectangle(14, 50, 15, 51))
#   for f in layer.getFeatures(request):
for feature in layer.features(bbox=(14, 50, 15, 51), limit=100):
    print(feature["name"], feature.geometry.area)

# Instead of:
#   edit_layer = iface.activeLayer()
#   edit_layer.startEditing()
#   ... do stuff ...
#   edit_layer.commitChanges()
with layer.editing():
    layer.add_feature(new_feature)
    layer.delete_feature(42)
    # Auto-commits on success, rolls back on exception

# Instead of:
#   transform = QgsCoordinateTransform(
#       layer.crs(),
#       QgsCoordinateReferenceSystem("EPSG:3857"),
#       QgsProject.instance()
#   )
#   transformed = transform.transform(geometry)
transformed = geometry.transform(from_crs=layer.crs, to_crs=crs.web_mercator)
```

### 1.4 Expression Engine

```python
from qgis_sdk import Expression

# Parse and evaluate
expr = Expression('"height" > 50 AND "type" = \'residential\'')
result = expr.evaluate(feature)  # → True

# Use as filter
for feature in layer.features(filter=Expression('"area" > 1000')):
    print(feature["name"])

# Compile for repeated evaluation (faster)
compiled = expr.compile(layer.fields)
for feature in layer.features():
    if compiled.evaluate_bool(feature):
        # ...
        pass
```

### 1.5 Geometry Operations

```python
from qgis_sdk import Geometry

# From WKT / WKB / GeoJSON
geom = Geometry.from_wkt("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
geom = Geometry.from_wkb(bytes_data)
geom = Geometry.from_geojson(geojson_dict)

# Properties
geom.type           # → "Polygon"
geom.area           # → 1.0
geom.length         # → 4.0
geom.centroid       # → Geometry(Point(0.5, 0.5))
geom.is_valid       # → True
geom.bbox           # → (0, 0, 1, 1)

# Operations (delegate to GEOS)
buffered = geom.buffer(0.1)
simplified = geom.simplify(0.01)
intersection = geom.intersection(other_geom)
union = geom.union(other_geom)
contains = geom.contains(point)
distance = geom.distance(other_geom)

# Export
geom.to_wkt()       # → "POLYGON((...))"
geom.to_wkb()       # → bytes
geom.to_geojson()   # → dict
```

---

## 2. Rust Acceleration — Retired

Rust acceleration is not part of the SDK, and it never shipped. This section
specified a `@rust_accelerated` decorator that loaded a compiled Rust module and
fell back to Python when the module was absent. Measured against the package
today there are **zero** occurrences of `rust_accelerated` and zero of `HAS_RUST`
anywhere under `py-packages/` or `crates/`.

[D15](decisions/D15-qgis-sdk-cli-pure-python-typer.md) §3, as amended by TASK-57,
rules the feature out rather than deferring it: qgis-sdk contains no Rust, so
there is no native module to load and no native/fallback parity to test. TASK-16,
which owned the implementation, is archived on that basis.

A plugin that wants a Rust hot path runs `cargo` itself and ships the resulting
extension in its own `extlibs/`. That is the plugin's build, not an SDK feature:
`qgis-sdk new` writes a Python-only tree, and no subcommand invokes `cargo`.

The section number is kept so the section map in
[doc-1](../backlog/docs/knowledge-backlog-map/doc-1%20-%20Knowledge-to-backlog-migration-map.md)
and the evidence table in §12 stay valid.

---

## 3. Unified API — Retired

This section specified `qgis_sdk.render`, `qgis_sdk.features`,
`qgis_sdk.geometry` and `qgis_sdk.crs`, each delegating to a Rust backend when
one was importable and to PyQGIS otherwise. None of the four modules exists:
there is no `render.py`, `features.py`, `geometry.py` or `crs.py` in the package,
and none of the 145 names in `qgis_sdk.__all__` is one of them. The
`qgis_render` fast path it fell back from is a crate of the standalone engine,
not something the SDK imports.

What the SDK actually offers over PyQGIS is §1 — decorators and builders for
plugins, algorithms, dialogs, bridges, network, tasks and styles.

The ergonomic wrappers this section assumed are still open work, and they are
specified against PyQGIS with no Rust behind them: `iface`, layers and CRS under
TASK-13, the expression engine under TASK-14, geometry under TASK-15.

---

## 4. Plugin Types

### 4.1 Processing Plugin (most common)

```python
from qgis_sdk import Plugin, Algorithm, parameter, output

class MyPlugin(Plugin):
    name = "My Algorithms"
    version = "0.1.0"

    algorithms = [
        BufferAdvanced,
        ClipByAttribute,
        MergeLayers,
    ]

class BufferAdvanced(Algorithm):
    id = "my_plugin:buffer"
    name = "Advanced Buffer"
    # ... (see section 1.2)

class ClipByAttribute(Algorithm):
    id = "my_plugin:clip_by_attr"
    name = "Clip by Attribute"
    # ...

class MergeLayers(Algorithm):
    id = "my_plugin:merge"
    name = "Merge Layers"
    # ...
```

### 4.2 Toolbar / Dialog Plugin

```python
from qgis_sdk import Plugin, action, toolbar, dialog

class MapNotes(Plugin):
    name = "Map Notes"
    version = "1.0.0"

    @toolbar("Map Notes")
    @action(icon="icons/note.svg", tooltip="Add a note to the map")
    def add_note(self, iface):
        """Click on the map to add a note."""
        tool = PointClickTool(iface.canvas, on_click=self._on_click)
        iface.set_map_tool(tool)

    def _on_click(self, point):
        dialog = NoteDialog(point)
        if dialog.exec():
            self._save_note(dialog.note)

    @action(icon="icons/list.svg", tooltip="View all notes")
    def list_notes(self, iface):
        panel = NotesPanel(self._notes)
        iface.add_dock_widget(panel)
```

### 4.3 Data Provider Plugin

```python
from qgis_sdk import Plugin, DataProvider, VectorSource

class MyFormatPlugin(Plugin):
    name = "My Format Support"
    version = "0.1.0"
    providers = [MyFormatProvider]

class MyFormatProvider(DataProvider):
    """Read .myf files as vector layers."""

    provider_id = "myformat"
    name = "My Custom Format"
    description = "Reads proprietary .myf files"
    extensions = ["myf"]

    def open(self, uri: str) -> VectorSource:
        reader = MyFormatReader(uri)
        return VectorSource(
            fields=reader.schema(),
            geometry_type=reader.geometry_type(),
            features=lambda request: reader.iter(request),
            feature_count=reader.count(),
            extent=reader.bbox(),
            crs=reader.crs(),
        )
```

### 4.4 Server Plugin

```python
from qgis_sdk import ServerPlugin, service, ogc_handler

class MyServerPlugin(ServerPlugin):
    """QGIS Server plugin that adds a custom API endpoint."""

    name = "Custom API"

    @service("/api/custom", methods=["GET"])
    def custom_endpoint(self, request, response):
        """Handle GET /api/custom?param=value"""
        param = request.param("param", default="world")
        response.write_json({"message": f"Hello, {param}!"})

    @ogc_handler("WMS", "GetMap")
    def modify_wms_request(self, request, response):
        """Intercept WMS GetMap requests to add watermark."""
        # Let QGIS render the map normally
        # Then overlay a watermark on the response image
        image = response.image()
        image.watermark("© My Company")
        response.set_image(image)
```

---

## 5. CLI: `qgis-sdk`

### 5.1 Commands

`qgis-sdk` is one pure-Python [typer](https://typer.tiangolo.com) application: a
console script calling `qgis_sdk.cli:main` (D15 §1). There is no Rust binary, no
native extension and no second name for it: the earlier alias was retired by D15
and nothing in the repository forwards to it. This is the shipped `--help`, not a
specification:

```
qgis-sdk [OPTIONS] COMMAND [ARGS]...

Commands:
  new        Scaffold a new plugin.
  validate   Check a plugin's structure and metadata.
  info       Show plugin information.
  version    Print the qgis-sdk version.
  build      Build and package the plugin.
  package    Zip the plugin package into an archive QGIS can install.
  test       Run the plugin's Python tests with pytest.
  install    Copy the plugin into a QGIS profile.
  dev        Watch mode: rebuild on file change (not implemented).
  publish    Upload an archive to the QGIS plugin repository (not implemented;
             use --dry-run).
  bootstrap  Write the bootstrap.py helper.
  vendor     Vendor wheels for offline installs.
  ui         Add UI scaffolding to a plugin.        (add-dialog, add-web)
  bridge     Generate bridge typings for web UIs.   (generate)
```

Two rules from D15 §3 govern every command above. A command either does its work
or exits non-zero — printing "Built" without writing the artifact is a defect,
which is why `dev` and `publish` advertise themselves as not implemented in
their own help text instead of pretending. And there is no `rust` group: `rust
init`, `rust build`, every `--rust` flag and the `cargo` passthrough were removed
by TASK-57.

### 5.2 `new`

```bash
qgis-sdk new my_plugin                      # name as a positional argument
qgis-sdk new my_plugin --type processing    # general | processing | provider | server
qgis-sdk new my_plugin --no-ui              # skip the dialog scaffolding
qgis-sdk new my_plugin --author "Ada" --email ada@example.com
qgis-sdk new my_plugin -o /tmp/out          # directory to create it in
qgis-sdk new my_plugin --web --framework react   # vanilla|react|vue|webcomponents|bun
qgis-sdk new my_plugin --bun                # Bun web UI, implies --declarative
```

**Prompts (D15 §2).** `questionary` asks for the plugin name, `--type`,
`--ui/--no-ui`, `--author` and `--email` — but only at a terminal, when stdin
*and* stdout are both TTYs, and only for questions whose flag was not given. Web
choices (`--web`, `--framework`) are flags only and never prompt. A
non-interactive run never blocks: with no name and no TTY, `new` exits `2` and
writes nothing. That is what makes the command safe in CI, and every prompt has a
flag that answers it.

**Generated structure** — Python only; there is no Rust variant, no `Cargo.toml`
and no `src/lib.rs`:

```
my_plugin/
├── pyproject.toml              # Python packaging
├── README.md
├── metadata.txt                # written from the METADATA_FIELDS table
├── my_plugin/
│   ├── __init__.py             # class_factory entry point
│   ├── plugin.py               # your plugin class
│   ├── algorithms/             # if --type processing
│   ├── dialogs/                # if --ui
│   └── icons/
├── tests/
│   ├── test_algorithms.py      # unit tests, no QGIS needed
│   └── test_integration.py     # integration tests, QGIS needed
└── .github/workflows/ci.yml
```

### 5.3 `build` and `package`

```bash
qgis-sdk build                      # → dist/<name>.zip
qgis-sdk build -o out               # choose the output directory
qgis-sdk package                    # same archive, explicit verb
qgis-sdk package --bundle           # also copy bootstrap.py into the package
qgis-sdk package --offline-wheel dist/qgis_sdk-*.whl   # vendor the wheel inside
```

There is no `--rust` and no `--all-targets`: the archive is a zip of Python
sources, so there is nothing per-platform to cross-build. `package` picks the
plugin package directory by name rather than taking the first child folder with
an `__init__.py`, which is what once made it zip `tests/` instead of the plugin
(TASK-57). By default the archive carries no `qgis_sdk` code; `--bundle` and
`--offline-wheel` are explicit opt-ins that do, for plugins that must
self-install offline.

### 5.4 `dev`, `install` and `publish`

```bash
qgis-sdk install --profile <path>   # copy the plugin into a QGIS profile
qgis-sdk dev --launch               # watch mode — NOT IMPLEMENTED, exits non-zero
qgis-sdk publish --zip dist/x.zip --dry-run   # checks the archive exists
qgis-sdk publish --zip dist/x.zip             # NOT IMPLEMENTED, exits non-zero
qgis-sdk test                       # run the plugin's pytest suite
```

`dev` and `publish` say so in their own help text and fail rather than pretend —
D15 §3 makes a command that reports work it did not do a defect. `publish
--dry-run` is the usable half: it verifies the archive without uploading. There
is no `--rust` on any of them, and no watch loop over `.rs` files.

### 5.5 `ui` and `bridge` — the subcommand groups

The two subcommand groups the CLI really has. `rust init` is gone: adding Rust
to an existing plugin is not an SDK operation any more (§2).

```bash
qgis-sdk ui add-dialog [path] --name my_dialog   # scaffolds a dialog
qgis-sdk ui add-web [path]                       # scaffolds a WebEngine page
qgis-sdk bridge generate ...                     # TypeScript typings for a bridge
```

`ui add-dialog` asks for the dialog name with `questionary` when `--name` is
omitted **and** the run is at a terminal; otherwise the missing name is an error.
That is the same TTY rule as `new` (D15 §2), and it is the only prompt outside
scaffolding.

---

## 6. Configuration: `plugin.toml`

> **Specified, not implemented.** `qgis-sdk new` writes `metadata.txt` directly
> (`scaffold.py`), and nothing in the package reads a `plugin.toml`. The format
> below is a design proposal owned by TASK-3, not a description of shipped
> behaviour. What is real today is `qgis_sdk.metadata`: the 20-entry
> `METADATA_FIELDS` table maps plugin attributes to `metadata.txt` keys in the
> order QGIS expects, and `render_metadata` / `render_metadata_from_dict` /
> `write_metadata` / `validate_metadata` drive it.

Replaces `metadata.txt`. More structured, generates metadata.txt at build time.

```toml
[plugin]
name = "My Plugin"
version = "0.1.0"
description = "Does useful things with vector data"
author = "Your Name"
email = "you@example.com"
qgis_min_version = "3.28"
category = "Vector"
tags = ["vector", "buffer", "geometry"]
icon = "icons/icon.svg"
homepage = "https://github.com/you/my-plugin"
repository = "https://github.com/you/my-plugin"
tracker = "https://github.com/you/my-plugin/issues"
experimental = false

[plugin.processing]
has_provider = true
provider_id = "my_plugin"
provider_name = "My Algorithms"

[plugin.dependencies]
# Python packages (installed via qpip)
# python_packages = ["requests>=2.28", "pandas"]

# QGIS plugin dependencies
# qgis_plugins = ["QuickOSM"]

[changelog]
"0.1.0" = "Initial release"
```

---

## 7. Testing

### 7.1 Unit Tests (no QGIS needed)

```python
# tests/test_algorithms.py
import pytest
from qgis_sdk.testing import mock_context, mock_source, mock_features

from my_plugin.algorithms.buffer import BufferAdvanced

def test_buffer_simple():
    algo = BufferAdvanced()
    ctx = mock_context({
        "input_layer": mock_source(mock_features(10, geometry_type="Point")),
        "distance": 5.0,
        "dissolve": False,
    })

    result = algo.process(ctx)
    output = result["output_layer"]

    assert output.feature_count == 10
    assert all(f.geometry.area > 0 for f in output.features())

def test_buffer_dissolve():
    algo = BufferAdvanced()
    ctx = mock_context({
        "input_layer": mock_source(mock_features(10, geometry_type="Point")),
        "distance": 100.0,
        "dissolve": True,
    })

    result = algo.process(ctx)
    output = result["output_layer"]

    # Dissolved: overlapping buffers merge
    assert output.feature_count < 10
```

### 7.2 Integration Tests (QGIS needed)

```python
# tests/test_integration.py
import pytest
from qgis_sdk.testing import qgis_app

def test_buffer_in_qgis(qgis_app):
    """Run the algorithm inside real QGIS Processing framework."""
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback
    from my_plugin.algorithms.buffer import BufferAdvanced

    algo = BufferAdvanced()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    result, ok = algo.run({
        "input_layer": "test_data/points.gpkg",
        "distance": 10.0,
        "dissolve": False,
    }, context, feedback)

    assert ok
    assert result["output_layer"].featureCount() == 100
```

### 7.3 Rust Tests — Retired

There are no Rust tests in a scaffolded plugin. The `tests/test_buffer.rs` file
this section showed came from a Cargo/PyO3 template that TASK-57 removed along
with the `rust` subcommand group (D15 §3 as amended). A plugin that adds its own
Rust extension tests it with `cargo test`, outside the SDK and outside this
document.

The two tiers that remain are §7.1, unit tests that need no QGIS, and §7.2,
integration tests that do.

---

## 8. Backend Selection — Retired

There is no backend selector. This section and §3 both specified
`qgis_sdk/_backend.py` choosing between a Rust module and a PyQGIS fallback at
import time. That file does not exist, and D15 §3 as amended removes the Rust
half of the choice, so there is nothing left to select between.

What the package does have is a **lazy-import** seam, which is easy to mistake
for a backend switch and is not one. Every PyQGIS access goes through
`qgis_sdk.runtime` — `qgis_core()`, `qgis_gui()`, `require_qgis()` — called from
inside functions rather than at module scope, so importing `qgis_sdk` never
imports `qgis` and the test suite runs on a machine with no QGIS at all. There
is exactly one backend: PyQGIS.

The capability flags exported in `qgis_sdk.__all__` — `HAS_CLI`, `HAS_UI`,
`HAS_TESTING`, `HAS_BRIDGE`, `HAS_NETWORK`, `HAS_TASKS`, `HAS_QT`, `HAS_STYLES` —
report whether an optional Qt or PyQGIS dependency imported. There is no
`HAS_RUST` among them, and no `RUST_VERSION`.

---

## 9. Product Structure

```
qgis-rust/
├── crates/                        # Rust — the standalone engine, not the SDK
│   ├── qgis-sys/                  #   native manager over the QGIS C ABI (D12)
│   ├── qgis-protocol/             #   versioned wire protocol (D09)
│   ├── qgis-engine/               #   capability handlers
│   ├── qgis-render/               #   headless rendering
│   ├── qgis-cli/                  #   the GIS-execution CLI (D13 §1)
│   ├── qgis-server/
│   ├── qgis-rs/, qgis-mcp/, qgis-styles/
│   └── xtask/                     #   repository automation (D10)
│
├── py-packages/
│   ├── qgis-sdk/                  # the SDK: pure Python, setuptools (D15 §4)
│   │   ├── src/qgis_sdk/
│   │   │   ├── plugin/            #   Plugin base, @action, @toolbar, @menu
│   │   │   ├── algorithm.py       #   Algorithm, parameter.*, output.*
│   │   │   ├── processing_bridge.py
│   │   │   ├── ui.py              #   Dialog, WebDialog, field, layout
│   │   │   ├── bridge/            #   QWebChannel bridge generation
│   │   │   ├── network.py         #   requests-like client
│   │   │   ├── tasks.py           #   celery-like task client
│   │   │   ├── styles.py          #   StyleSheet, LayerStyle, StyleRenderer
│   │   │   ├── metadata.py        #   METADATA_FIELDS → metadata.txt
│   │   │   ├── runtime.py         #   lazy qgis_core()/qgis_gui()/require_qgis()
│   │   │   ├── scaffold.py        #   the trees `qgis-sdk new` writes
│   │   │   ├── cli.py             #   the typer application (D15)
│   │   │   ├── installer.py, bootstrap.py
│   │   │   └── testing/           #   FakeIface, mock_context, fake factories
│   │   └── pyproject.toml         #   setuptools; typer + questionary
│   └── qgis-py/                   # standalone engine client — keeps maturin
│
├── ts-packages/                   # qgis-node addon; @archont561/qgis-sdk web client
├── docs/                          # the published docs site
└── .knowledge/
    ├── api-design.md
    └── qgis-sdk.md                # this document
```

Three corrections to the tree this section used to carry. `crates/qgis-sdk` and
`crates/qgis-sdk-core` do not exist — they were removed in `2d8d69a` — and
`qgis-cli` is the GIS-execution CLI only; plugin tooling does not enter it
(D15 §1). There is no top-level `python/` or `templates/` directory: the Python
distributions live under `py-packages/`, and `qgis-sdk new` renders its trees
from `scaffold.py` rather than copying templates. `qgis-py` keeps `maturin` for
its own PyO3 extension; `qgis-sdk` does not (D15 §4).

---

## 10. Planning ownership

Effort estimates, phase sequencing, priorities, and next actions are Backlog.md
concerns rather than durable SDK knowledge. The former estimate and phase model
were moved to the [Backlog execution roadmap](../backlog/docs/roadmap/doc-2%20-%20QGIS-RS-Execution-Roadmap.md),
with current ownership represented by milestone `m-3` and its linked tasks.

---

## 11. Comparison with Alternatives

| Feature | Raw PyQGIS | Plugin Builder | qgis-sdk |
|---------|-----------|---------------|----------|
| Boilerplate | Write manually | Generates once | Eliminates (decorators) |
| API style | C++-ish, verbose | Same as PyQGIS | Pythonic, type-hinted |
| Testing | Must run in QGIS | No support | Unit tests without QGIS |
| Packaging | Manual .zip | No support | `qgis-sdk package` |
| Publishing | Manual upload | No support | `qgis-sdk publish` |
| Rust support | No | No | No — removed by D15 §3 |
| Cross-platform | Build per OS | No support | One pure-Python zip |
| Processing GUI | Manual param defs | Same | Declarative decorators |
| Learning curve | Steep | Medium | Low |

---

## 12. Implementation Evidence and Backlog Tracking

The SDK lives at **`py-packages/qgis-sdk/`** as a pixi workspace package, as a pure-Python
pixi package (`pixi.toml` with a `[package]` section + `pyproject.toml` with setuptools; D15).
See [pixi.md](/pixi.md) for how the workspace and the PyQGIS import paths are
wired up.

This table is an evidence snapshot, not a second status source. Current work,
acceptance criteria, and next actions live in [TASK-1](../backlog/tasks/task-1%20-%20Make%20the%20full%20QGIS%20SDK%20test%20suite%20headless%20and%20CI-green.md),
[TASK-2](../backlog/tasks/task-2%20-%20Add%20a%20dedicated%20QGIS%20SDK%20integration%20test%20runner%20and%20CI%20job.md),
[TASK-3](../backlog/tasks/task-3%20-%20Document%20and%20scaffold%20the%20declarative%20plugin%20and%20SDK%20APIs.md),
[TASK-4](../backlog/tasks/task-4%20-%20Cover%20real%20QGIS%20network%20and%20task-manager%20integration.md),
[TASK-13](../backlog/tasks/task-13%20-%20Implement-ergonomic-PyQGIS-wrappers-for-iface-layers-and-CRS.md)
through [TASK-18](../backlog/tasks/task-18%20-%20Add-frontend-framework-starter-templates-for-WebEngine-plugins.md),
and [TASK-57](../backlog/tasks/task-57%20-%20Make-qgis-sdk-a-pure-Python-PyQGIS-plugin-CLI-with-typer-and-questionary.md).

The product boundary is specified in [doc-7](../backlog/docs/architecture/doc-7%20-%20Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md) and decided by [D13](decisions/D13-rust-cli-ffi-and-qgis-sdk-boundaries.md) as amended by [D15](decisions/D15-qgis-sdk-cli-pure-python-typer.md). [TASK-40](../backlog/tasks/task-40%20-%20Define-Rust-CLI-FFI-and-QGIS-SDK-product-boundaries.md) records and tests the contract; TASK-41 through TASK-43 still carry the standalone CLI, the cross-language FFI clients and the hosted-runtime separation. Two owners named here before are gone: TASK-26 is archived, because the shared Rust/wire CLI refactor it described is what D15 reversed, and TASK-44's Rust-native packaging framing is superseded by the same record.

| Spec section | Module | Evidence / backlog owner |
|--------------|--------|--------|
| 1.1 Plugin definition, decorators | `qgis_sdk.plugin` — `Plugin`, `@action`, `@toolbar`, `@menu`, `class_factory` | Implemented, unit-tested |
| 1.1 `metadata.txt` generation | `qgis_sdk.metadata` — `render_metadata`, `write_metadata` | Implemented, unit-tested |
| 1.2 Processing algorithms | `qgis_sdk.algorithm` — `Algorithm`, `parameter.*`, `output.*` | Declarative model implemented, unit-tested |
| 1.2 QGIS Processing bridge | `qgis_sdk.processing_bridge` — `build_algorithm`, `_ContextAdapter` | Written against PyQGIS; runtime proof and lifecycle coverage → TASK-4 |
| Toolbar/menu widgets | `qgis_sdk.qt` — `make_action` | Written against `qgis.PyQt`; runtime proof and lifecycle coverage → TASK-4 |
| 1.3 Cleaner PyQGIS wrappers (`iface`, `layers`, `crs`, …) | — | Specification/open implementation → TASK-13 |
| 1.4 Expression engine wrappers | — | Specification/open implementation → TASK-14 |
| 1.5 Geometry wrappers | — | Specification/open implementation → TASK-15 |
| 2 Rust acceleration | — | Retired by D15 §3 as amended; TASK-16 archived |
| 1.1 UI dialogs (Qt Designer .ui + declarative) | `qgis_sdk.ui` — `Dialog`, `field`, `layout`, `Button`, `@dialog`, `make_dialog` | Implemented evidence; UI/template follow-up → TASK-18 |
| 1.1 WebEngine HTML + QWebChannel | `qgis_sdk.ui` — `WebDialog`, `@web_bridge`, `make_web_view` | Implemented evidence; bridge/package follow-up → TASK-18 |
| 5 CLI (`qgis-sdk new/validate/build/package/test/install`) | `qgis_sdk.cli` — pure-Python typer app (D15) | Implemented and unit-tested → TASK-57; `dev` and `publish` still unimplemented → TASK-17 |
| 5 UI scaffolding | `qgis-sdk new --web`, `ui/*.ui`, `web/map.html` (Leaflet + qrc:///qtwebchannel/qwebchannel.js) | Implemented evidence; docs/scaffold follow-up → TASK-3/TASK-18 |
| 7 Testing story | `tests/` — fake interface + fake action factory | Pure-Python evidence exists; headless/runtime/fixture proof → TASK-1/TASK-2/TASK-23 |

### Why nothing imports `qgis` at module scope

Section 7 promises unit tests that do not need QGIS. To keep that promise,
every PyQGIS access goes through `qgis_sdk.runtime` (`qgis_core()`,
`qgis_gui()`, `require_qgis()`), called from inside functions. The test-suite
injects a fake interface and an `action_factory`, so plugin and algorithm logic
is exercised on a machine with no QGIS at all:

```bash
# the SDK suite, no QGIS required — 490 passed, 3 skipped, 8 deselected
pixi run -- bun x turbo run test --filter=qgis-sdk-py
```

The turbo package is `qgis-sdk-py`, not `qgis-sdk`. The `sdk-test` and
`sdk-doctor` pixi tasks this document used to name do not exist; the qt and qgis
tiers of the same suite are deselected by default and run under their own pixi
tasks, which need a display and a QGIS install.
