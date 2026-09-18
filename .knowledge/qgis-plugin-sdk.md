---
type: concept
title: "QGIS Plugin SDK — Python-First with Optional Rust"
description: "Python framework for building QGIS plugins with a clean API that wraps PyQGIS or Rust bindings. Users write Python, optionally accelerate with Rust. CLI handles scaffolding, testing, packaging, and deployment."
tags: [plugin, sdk, python, rust, pyo3, qgis, cli, tooling]
generated: "2026-09-17T17:30:00Z"
status: draft
---

# QGIS Plugin SDK

A Python framework for building QGIS plugins — in Python, Rust, or both.

## Philosophy

```
qgis-sdk = better PyQGIS + optional Rust + CLI tooling

   PyQGIS (raw)          qgis-sdk
   ─────────────         ─────────────────
   verbose               decorators + builders
   C++-ish API           Pythonic API
   no packaging          CLI: scaffold → test → package → publish
   Python-only           Python + optional Rust hotspots
   no testing story      unit tests without QGIS
```

Users write Python. The SDK provides cleaner wrappers around PyQGIS, eliminates boilerplate, and lets them drop into Rust when Python isn't fast enough.

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

## 2. Rust Acceleration — Drop-In

When Python is too slow, drop into Rust for the hot path. The SDK makes this seamless.

### 2.1 Mark a method as Rust-accelerated

```python
from qgis_sdk import Algorithm, parameter, output, rust_accelerated

class BufferFast(Algorithm):
    """Fast buffer — uses Rust when available, falls back to PyQGIS."""

    id = "my_plugin:buffer_fast"
    name = "Fast Buffer"

    input_layer = parameter.source("Input layer")
    distance = parameter.distance("Buffer distance", default=10.0)
    output_layer = output.sink("Buffered")

    # Try to use Rust implementation, fall back to Python
    @rust_accelerated(fallback="process_python")
    def process(self, context):
        """Rust implementation (defined in src/lib.rs)."""
        pass  # This body is replaced by the Rust module

    def process_python(self, context):
        """Pure Python fallback."""
        source = context.get(self.input_layer)
        dist = context.get(self.distance)
        sink = context.create_sink(self.output_layer, ...)

        for feature in source.features():
            buffered = feature.geometry.buffer(dist)
            out = feature.clone()
            out.geometry = buffered
            sink.add_feature(out)

        return {self.output_layer: sink}
```

### 2.2 The Rust module (optional)

```rust
// src/lib.rs
use qgis_plugin_sdk::prelude::*;
use pyo3::prelude::*;

/// Rust-accelerated buffer processing.
/// Called automatically when available, falls back to Python.
#[pyfunction]
fn buffer_features(
    input_path: &str,
    distance: f64,
    output_path: &str,
    progress_callback: &PyAny,
) -> PyResult<()> {
    let input = open_source(input_path)?;
    let mut output = create_sink(output_path, &input)?;

    let total = input.feature_count();
    let features: Vec<_> = input.features()
        .par_bridge()  // rayon parallel
        .map(|f| {
            let geom = f.geometry();
            let buffered = geom.buffer(distance)?;
            let mut out = Feature::from(&f);
            out.set_geometry(buffered);
            Ok(out)
        })
        .collect::<Result<Vec<_>>>()?;

    for (i, f) in features.iter().enumerate() {
        output.add_feature(f)?;
        if i % 100 == 0 {
            progress_callback.call1((i as f64 / total as f64,))?;
        }
    }

    Ok(())
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(buffer_features, m)?)?;
    Ok(())
}
```

### 2.3 Import the Rust module in Python

```python
# The SDK handles loading the Rust module
try:
    from my_plugin._native import buffer_features
    HAS_RUST = True
except ImportError:
    HAS_RUST = False

class BufferFast(Algorithm):
    def process(self, context):
        if HAS_RUST:
            # Use Rust implementation (10-100x faster)
            buffer_features(
                context.source_path(self.input_layer),
                context.get(self.distance),
                context.sink_path(self.output_layer),
                context.set_progress,
            )
        else:
            # Fall back to PyQGIS
            self.process_python(context)
```

The `@rust_accelerated` decorator automates this pattern.

---

## 3. Unified API — PyQGIS or Rust, Same Interface

The SDK provides a unified API that can delegate to either PyQGIS or Rust bindings, depending on what's available:

```python
from qgis_sdk import render, features, geometry, crs

# Rendering — uses Rust qgis-render if available, else QGIS C++
image = render.project("map.qgs", width=1024, height=768)
image.save("map.png")

# Feature access — uses Rust bindings if available, else PyQGIS
layer = features.open("buildings.gpkg")
for f in layer.features(bbox=(14, 50, 15, 51)):
    print(f["name"], f.geometry.area)

# Geometry ops — uses Rust (GEOS) if available, else PyQGIS (also GEOS)
geom = geometry.from_wkt("POLYGON((...))")
buffered = geom.buffer(10.0)

# CRS transforms — uses Rust (proj) if available, else PyQGIS (also PROJ)
wgs84 = crs.from_epsg(4326)
mercator = crs.web_mercator
x, y = crs.transform(14.0, 50.0, from_crs=wgs84, to_crs=mercator)
```

**How it works under the hood:**

```python
# qgis_sdk/render.py (simplified)

def project(path, width=1024, height=768, **kwargs):
    """Render a QGIS project to an image."""
    try:
        # Fast path: Rust qgis-render
        from qgis_render import Project, RenderSettings
        proj = Project.open(path)
        return proj.render(RenderSettings(width, height, **kwargs))
    except ImportError:
        # Slow path: PyQGIS
        from qgis.core import QgsProject, QgsMapSettings, QgsMapRendererSequentialJob
        proj = QgsProject.instance()
        proj.read(path)
        settings = QgsMapSettings()
        settings.setOutputSize(QSize(width, height))
        # ... configure from kwargs ...
        job = QgsMapRendererSequentialJob(settings)
        job.start()
        job.waitForFinished()
        return Image(job.renderedImage())
```

Users call `render.project()` and get the best available backend automatically.

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

## 5. CLI: `qgis-plugin`

### 5.1 Commands

```
qgis-plugin <command> [options]

Commands:
  new         Scaffold a new plugin project
  build       Build and package the plugin
  test        Run tests (Python + optional Rust)
  install     Install into local QGIS
  dev         Watch mode: rebuild on file change
  package     Create .zip for QGIS Plugin Repository
  publish     Upload to QGIS Plugin Repository
  validate    Check plugin structure and metadata
  rust init   Add Rust acceleration to an existing plugin
  rust build  Build the Rust module
```

### 5.2 `new`

```bash
# Pure Python plugin (default)
qgis-plugin new my-plugin

# Python + Rust plugin
qgis-plugin new my-plugin --rust

# Processing-only plugin
qgis-plugin new my-algorithms --type processing

# Interactive
qgis-plugin new
# → Plugin name: my-plugin
# → Type: [general] processing provider server
# → Include Rust acceleration? [y/N]
# → Author: Your Name
# → Email: you@example.com
```

**Generated structure (Python-only):**

```
my-plugin/
├── pyproject.toml              # Python packaging
├── plugin.toml                 # Plugin config (generates metadata.txt)
├── README.md
├── my_plugin/
│   ├── __init__.py             # Auto-generated from plugin class
│   ├── plugin.py               # Your plugin class
│   ├── algorithms/             # Processing algorithms (if type=processing)
│   │   └── buffer.py
│   ├── dialogs/                # Qt dialogs (if type=general)
│   └── icons/
│       └── icon.svg
├── tests/
│   ├── test_algorithms.py      # Unit tests (no QGIS needed)
│   └── test_integration.py     # Integration tests (QGIS needed)
└── .github/
    └── workflows/ci.yml
```

**Generated structure (Python + Rust):**

```
my-plugin/
├── pyproject.toml
├── plugin.toml
├── Cargo.toml                  # Rust project
├── README.md
├── my_plugin/
│   ├── __init__.py
│   ├── plugin.py
│   └── algorithms/
│       └── buffer.py
├── src/                        # Rust source
│   └── lib.rs                  # PyO3 module
├── tests/
│   ├── test_algorithms.py
│   ├── test_rust.py            # Rust unit tests
│   └── test_integration.py
└── .github/
    └── workflows/ci.yml
```

### 5.3 `build`

```bash
# Build Python-only plugin
qgis-plugin build
# → dist/my_plugin-0.1.0.zip

# Build with Rust (current platform)
qgis-plugin build --rust
# → dist/my_plugin-0.1.0-linux-x86_64.zip

# Build with Rust (all platforms)
qgis-plugin build --rust --all-targets
# → dist/my_plugin-0.1.0-linux-x86_64.zip
# → dist/my_plugin-0.1.0-windows-x86_64.zip
# → dist/my_plugin-0.1.0-macos-arm64.zip
# → dist/my_plugin-0.1.0-macos-x86_64.zip
```

### 5.4 `dev` — Watch mode

```bash
# Pure Python: watch .py files, reinstall on change
qgis-plugin dev

# With Rust: watch .py and .rs files, rebuild + reinstall
qgis-plugin dev --rust

# Launch QGIS after install
qgis-plugin dev --launch
```

### 5.5 `rust init` — Add Rust to existing plugin

```bash
# You have an existing Python plugin and want to add Rust acceleration
cd my-existing-plugin/
qgis-plugin rust init
# → Creates Cargo.toml, src/lib.rs
# → Adds @rust_accelerated examples to your algorithms
# → Updates pyproject.toml with maturin build config
```

---

## 6. Configuration: `plugin.toml`

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

[plugin.rust]
enabled = false              # Set to true to enable Rust acceleration
module_name = "_native"      # Name of the Rust PyO3 module

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

### 7.3 Rust Tests (no QGIS needed)

```rust
// tests/test_buffer.rs
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_buffer_rust() {
        let features = mock_point_features(10);
        let result = buffer_features_inner(&features, 5.0);
        assert_eq!(result.len(), 10);
        assert!(result.iter().all(|f| f.geometry().area() > 0.0));
    }
}
```

---

## 8. The Unified API — How It Decides

```python
# qgis_sdk/_backend.py

import importlib

def _try_import(rust_module: str, pyqgis_fallback: str):
    """Try Rust first, fall back to PyQGIS."""
    try:
        return importlib.import_module(rust_module)
    except ImportError:
        return importlib.import_module(pyqgis_fallback)

# Rendering backend
render = _try_import("qgis_render", "qgis_sdk._pyqgis_render")

# Feature access backend
features = _try_import("qgis_render.features", "qgis_sdk._pyqgis_features")

# Geometry backend
geometry = _try_import("qgis_render.geometry", "qgis_sdk._pyqgis_geometry")

# CRS backend
crs = _try_import("qgis_render.crs", "qgis_sdk._pyqgis_crs")
```

Users import from `qgis_sdk` and get the best available backend:

```python
from qgis_sdk import render, features, geometry, crs

# If qgis-render (Rust) is installed → uses Rust
# If only PyQGIS is available → uses PyQGIS wrapper
# Same API either way
```

---

## 9. Product Structure

```
qgis-rs/
├── crates/
│   ├── qgis-sys/               # CXX FFI (low-level QGIS bindings)
│   ├── qgis-render/            # Core rendering engine (Rust)
│   ├── qgis-plugin-sdk/        # Rust acceleration library (PyO3)
│   ├── qgis-server/            # HTTP server
│   └── qgis-cli/               # CLI binary (includes qgis-plugin)
│
├── python/
│   ├── qgis-sdk/               # Python package (pip install qgis-sdk)
│   │   ├── qgis_sdk/
│   │   │   ├── __init__.py
│   │   │   ├── plugin.py       # Plugin base class
│   │   │   ├── algorithm.py    # Algorithm base class
│   │   │   ├── parameter.py    # Parameter types
│   │   │   ├── provider.py     # DataProvider base class
│   │   │   ├── wrappers/       # PyQGIS wrappers (cleaner API)
│   │   │   │   ├── layer.py
│   │   │   │   ├── feature.py
│   │   │   │   ├── geometry.py
│   │   │   │   ├── crs.py
│   │   │   │   └── iface.py
│   │   │   ├── _backend.py     # Rust/PyQGIS backend selector
│   │   │   ├── _pyqgis_render.py   # PyQGIS fallback for rendering
│   │   │   ├── _pyqgis_features.py # PyQGIS fallback for features
│   │   │   └── testing.py      # Test helpers (mock_context, etc.)
│   │   └── pyproject.toml
│   └── qgis-sdk-cli/           # Python CLI wrapper (thin shim over Rust CLI)
│
├── templates/                   # Scaffolding templates for `qgis-plugin new`
│   ├── python-only/
│   ├── python-rust/
│   ├── processing/
│   ├── general/
│   ├── provider/
│   └── server/
│
└── .knowledge/
    ├── api-design.md
    └── qgis-plugin-sdk.md      # This document
```

---

## 10. Effort Estimate

| Component | Effort | Priority |
|-----------|--------|----------|
| **Python SDK** (Plugin, Algorithm, Parameter base classes) | 3-4 weeks | P0 |
| **PyQGIS wrappers** (cleaner API: layer, feature, geometry, crs, iface) | 2-3 weeks | P0 |
| **CLI** (new, build, test, install, dev, package, publish) | 3-4 weeks | P0 |
| **Testing framework** (mock_context, mock_source, qgis_app fixture) | 2 weeks | P0 |
| **Templates** (scaffolding for `qgis-plugin new`) | 1 week | P0 |
| **plugin.toml → metadata.txt generator** | 2 days | P0 |
| **Rust SDK crate** (PyO3 acceleration library) | 3-4 weeks | P1 |
| **@rust_accelerated decorator** | 1 week | P1 |
| **Cross-platform build** (Rust for Win/Mac/Linux) | 2 weeks | P1 |
| **Unified backend selector** (Rust vs PyQGIS dispatch) | 1 week | P1 |
| **GitHub Actions template** | 2 days | P1 |
| **Documentation + examples** | 2-3 weeks | P1 |
| **Total** | **20-27 weeks** | |

### Phase 1 (Weeks 1-10): Python-only SDK
- Base classes, PyQGIS wrappers, CLI, testing, templates
- Users can write Python plugins with clean API
- `qgis-plugin new → dev → build → publish` workflow works

### Phase 2 (Weeks 11-18): Rust acceleration
- Rust SDK crate, @rust_accelerated, cross-platform builds
- Users can drop into Rust for hot paths
- Unified API that uses Rust when available

### Phase 3 (Weeks 19-27): Rendering integration
- Unified render/features/geometry/crs API
- qgis-render as optional backend
- Full ecosystem: plugin SDK + render engine + server

---

## 11. Comparison with Alternatives

| Feature | Raw PyQGIS | Plugin Builder | qgis-sdk |
|---------|-----------|---------------|----------|
| Boilerplate | Write manually | Generates once | Eliminates (decorators) |
| API style | C++-ish, verbose | Same as PyQGIS | Pythonic, type-hinted |
| Testing | Must run in QGIS | No support | Unit tests without QGIS |
| Packaging | Manual .zip | No support | `qgis-plugin package` |
| Publishing | Manual upload | No support | `qgis-plugin publish` |
| Rust support | No | No | First-class |
| Cross-platform | Build per OS | No support | `--all-targets` |
| Processing GUI | Manual param defs | Same | Declarative decorators |
| Learning curve | Steep | Medium | Low |

---

## 12. Implementation Status

The SDK lives at **`packages/qgis-sdk/`** as a pixi workspace package
(`pixi.toml` with a `[package]` section + `pyproject.toml` with hatchling).
See [pixi.md](/pixi.md) for how the workspace and the PyQGIS import paths are
wired up.

| Spec section | Module | Status |
|--------------|--------|--------|
| 1.1 Plugin definition, decorators | `qgis_sdk.plugin` — `Plugin`, `@action`, `@toolbar`, `@menu`, `class_factory` | Implemented, unit-tested |
| 1.1 `metadata.txt` generation | `qgis_sdk.metadata` — `render_metadata`, `write_metadata` | Implemented, unit-tested |
| 1.2 Processing algorithms | `qgis_sdk.algorithm` — `Algorithm`, `parameter.*`, `output.*` | Declarative model implemented, unit-tested |
| 1.2 QGIS Processing bridge | `qgis_sdk.processing_bridge` — `build_algorithm`, `_ContextAdapter` | Written against PyQGIS; **not yet run against a QGIS environment** |
| Toolbar/menu widgets | `qgis_sdk.qt` — `make_action` | Written against `qgis.PyQt`; **not yet run against a QGIS environment** |
| 1.3 Cleaner PyQGIS wrappers (`iface`, `layers`, `crs`, …) | — | Not started |
| 1.4 Expression engine wrappers | — | Not started |
| 1.5 Geometry wrappers | — | Not started |
| 2 Rust acceleration (`@rust_accelerated`) | — | Not started |
| 5 CLI (`qgis-plugin scaffold/test/package/publish`) | — | Not started |
| 7 Testing story | `tests/` — 35 tests, fake interface + fake action factory | Implemented; runs without QGIS |

### Why nothing imports `qgis` at module scope

Section 7 promises unit tests that do not need QGIS. To keep that promise,
every PyQGIS access goes through `qgis_sdk.runtime` (`qgis_core()`,
`qgis_gui()`, `require_qgis()`), called from inside functions. The test-suite
injects a fake interface and an `action_factory`, so plugin and algorithm logic
is exercised on a machine with no QGIS at all:

```bash
pixi run -e sdk sdk-test      # 35 tests, no QGIS required
pixi run -e sdk sdk-doctor    # proves import qgis.core resolves in the env
```
