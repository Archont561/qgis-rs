---
type: Decision
id: D07
title: "Project Scope — Rust QGIS Plugins via PyO3"
description: "Pivot to Rust computation engines behind QGIS Processing plugins via PyO3, bypassing CXX entirely."
status: draft
tags: [scope, pyo3, plugins, architecture, pivot]
date: 2026-09-17T00:00:00Z
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# D07: Rust QGIS Plugins via PyO3

## The Existential Question

**Is qgis-rs (as a QGIS C++ → Rust binding) even needed?**

No. The Rust geospatial ecosystem already covers what `QgsVectorLayer` + `QgsGeometry` + `QgsCRS` provide:

| QGIS class | Already covered by | Maturity |
|------------|-------------------|----------|
| `QgsVectorLayer` (data access) | `gdal` (OGR, 250+ formats) | Production |
| `QgsGeometry` (spatial ops) | `geo` + `geos` | Production |
| `QgsCoordinateReferenceSystem` | `proj` | Production |
| `QgsFeatureIterator` | `gdal::vector::Layer` | Production |
| `QgsProject` (XML) | Could parse XML directly | Trivial |

And [OxiGIS](https://github.com/cool-japan/oxigis) is building a pure-Rust QGIS alternative with zero FFI.

## What QGIS Actually Needs from Rust

**Computation engines behind QGIS Processing algorithms.**

QGIS's Processing framework (`QgsProcessingAlgorithm`) is the primary extension point. Algorithms receive features, process them, and return results. Most are written in Python and are **painfully slow** for large datasets.

The opportunity: write the computation core in Rust, wrap it as a PyO3 module, plug it into QGIS as a Processing provider.

## The Architecture

```
┌──────────────────────────────────────────────────┐
│                    QGIS Desktop                   │
│                                                   │
│  Processing Toolbox                               │
│  ┌─────────────────────────────────────────────┐ │
│  │ Rust Algorithms Provider                    │ │
│  │ ┌─────────────────────────────────────────┐ │ │
│  │ │ Python: MyAlgorithm(QgsProcessingAlgo)  │ │ │
│  │ │   processAlgorithm():                   │ │ │
│  │ │     wkb = feature.geometry().asWkb()    │ │ │
│  │ │     result = rust_engine.buffer(wkb, d) │ │ │
│  │ │     return result                       │ │ │
│  │ └────────────────┬────────────────────────┘ │ │
│  │                  │ PyO3 / import             │ │
│  │ ┌────────────────▼────────────────────────┐ │ │
│  │ │ Rust: rust_engine.so (cdylib)           │ │ │
│  │ │   use geo::algorithm::buffer::Buffer;   │ │ │
│  │ │   use rayon::prelude::*;                │ │ │
│  │ │   #[pyfunction]                         │ │ │
│  │ │   fn buffer(wkb: &[u8], d: f64) -> Vec  │ │ │
│  │ └─────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### Layers

| Layer | Language | Responsibility |
|-------|----------|----------------|
| QGIS | C++/Qt | Application, UI, data I/O, signal/slot |
| Python plugin | Python | QGIS API access, Processing registration, UI glue |
| Rust engine | Rust | Computation, parallelism, geo algorithms |

### Data Flow

```
PyQGIS                    Rust Engine
───────                   ───────────
feature.geometry()
  .asWkb()        ──►   &[u8] WKB bytes
                         │
                         ▼
                    geo_types::Geometry
                    (via wkb crate)
                         │
                    geo::Buffer / geos::buffer
                    rayon::par_iter() for batch
                         │
                         ▼
                    Vec<u8> WKB bytes
                  ◄──    (or Vec of results)
                  
QgsGeometry
  .fromWkb(result)
```

## Why This Works

### 1. No FFI pain with Qt or QGIS C++

Python handles ALL Qt/QGIS interaction. Rust only receives and returns **bytes and numbers**. No QObject, no signals, no QString, no implicit sharing, no ownership model, no threading issues.

### 2. The Rust geo ecosystem is better than QGIS internals

| Operation | QGIS (Python) | Rust engine |
|-----------|---------------|-------------|
| Buffer 100k polygons | ~45 seconds | ~0.8 seconds (rayon, 8 cores) |
| Spatial join | Nested loop O(n²) | `geo-index` R-tree O(n log n) |
| Voronoi | GEOS via Python | `geo::Voronoi` + rayon |
| Line simplification | Python loop | `simplify` crate, SIMD |

### 3. Processing algorithms are the right abstraction

`QgsProcessingAlgorithm` provides:
- Automatic UI (parameter dialogs)
- Progress reporting (`feedback.setProgress()`)
- Cancellation (`feedback.isCanceled()`)
- Model builder integration
- Batch processing
- Scripting access (`processing.run("rust:buffer", {...})`)

### 4. Distribution is solved

The plugin ships as:
```
my_rust_plugin/
├── __init__.py           # ~20 lines, registers provider
├── metadata.txt          # QGIS plugin metadata
├── provider.py           # QgsProcessingProvider subclass
├── algorithms/
│   ├── buffer.py         # Python shim → calls Rust
│   ├── spatial_join.py
│   └── ...
└── lib/
    ├── linux/
    │   └── rust_engine.cpython-312-x86_64-linux-gnu.so
    ├── macos/
    │   └── rust_engine.cpython-312-arm64-darwin.so
    └── windows/
        └── rust_engine.cp312-win_amd64.pyd
```

Built with `maturin` (the PyO3 build tool), per platform.

## What Changes in qgis-rs

### Remove (or deprioritize)

- CXX bridges for QGIS C++ types
- The opaque handle pattern
- `QgsApplication` lifecycle management
- Qt dependency at the Rust level

### Add

- **PyO3** as the bridge (replaces CXX)
- **maturin** as the build tool (replaces pixi for the Rust crate)
- **geo / geos / proj** as computation dependencies
- **wkb / wkt** crates for geometry serialization
- **rayon** for parallel feature processing

### Keep

- The knowledge base (.knowledge/)
- The pixi environment for testing (QGIS is still needed to test plugins)
- The pixi-sandbox provisioning for CI

## Example: A Rust-Backed Processing Algorithm

### Rust side (`src/lib.rs`)

```rust
use pyo3::prelude::*;
use geo::algorithm::buffer::Buffer;
use wkb::reader::read_wkb;
use wkb::writer::write_wkb;

#[pyfunction]
fn buffer_geometries(wkb_list: Vec<Vec<u8>>, distance: f64) -> PyResult<Vec<Vec<u8>>> {
    use rayon::prelude::*;
    
    let results: Vec<Vec<u8>> = wkb_list
        .par_iter()
        .map(|wkb_bytes| {
            let geom = read_wkb(wkb_bytes).unwrap();
            let buffered = geom.buffer(distance);
            write_wkb(&buffered).unwrap()
        })
        .collect();
    
    Ok(results)
}

#[pymodule]
fn rust_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(buffer_geometries, m)?)?;
    Ok(())
}
```

### Python plugin side (`algorithms/buffer.py`)

```python
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSink,
    QgsFeatureSink,
    QgsGeometry,
)
import rust_engine  # imports the Rust .so

class RustBufferAlgorithm(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    DISTANCE = 'DISTANCE'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, 'Input layer'))
        self.addParameter(QgsProcessingParameterNumber(
            self.DISTANCE, 'Buffer distance', defaultValue=100.0))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, 'Output layer'))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        distance = self.parameterAsDouble(parameters, self.DISTANCE, context)
        
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            source.fields(), source.wkbType(), source.sourceCrs())

        # Batch: collect all WKB, send to Rust at once
        wkb_list = []
        features = list(source.getFeatures())
        total = len(features)
        
        for f in features:
            wkb_list.append(bytes(f.geometry().asWkb()))
        
        # ONE call to Rust — parallel processing inside
        results = rust_engine.buffer_geometries(wkb_list, distance)
        
        for i, (feature, result_wkb) in enumerate(zip(features, results)):
            if feedback.isCanceled():
                break
            feature.setGeometry(QgsGeometry.fromWkb(result_wkb))
            sink.addFeature(feature, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(i / total * 100))

        return {self.OUTPUT: dest_id}

    def name(self): return 'rust_buffer'
    def displayName(self): return 'Buffer (Rust)'
    def group(self): return 'Rust Tools'
    def groupId(self): return 'rust'
    def createInstance(self): return RustBufferAlgorithm()
```

## Candidate Algorithms for Rust Backend

| Algorithm | Why Rust | Key Crate |
|-----------|----------|-----------|
| Buffer | Computation-heavy, parallelizable | `geo::Buffer` + `rayon` |
| Spatial join | R-tree indexing beats nested loops | `geo-index` + `rayon` |
| Voronoi / Delaunay | Computation-heavy | `geo::Voronoi` |
| Line simplification | Per-vertex, parallelizable | `simplify` |
| Convex hull | Per-feature | `geo::ConvexHull` |
| Centroid | Per-feature | `geo::Centroid` |
| Distance matrix | O(n²), benefits from SIMD | `geo::EuclideanDistance` |
| Cluster analysis | DBSCAN, K-means | `linfa-clustering` |
| Raster zonal stats | Pixel iteration | `ndarray` + `rayon` |

## Relationship to Existing qgis-rs Work

| Existing artifact | Keep? | How |
|-------------------|-------|-----|
| `crates/qgis-sys/` | **Deprecate** | Keep as reference, don't extend |
| `pixi.toml` | **Keep** | For testing plugins in QGIS |
| Scaffold task | **Repurpose** | Template for Rust Processing algorithms |
| Knowledge base | **Keep & update** | Add PyO3, Processing docs |
| CI / pixi-sandbox | **Keep** | For building .so per platform |
| `.knowledge/decisions/D01-D06` | **Supersede** | D07 replaces the two-crate + CXX approach |

## Risks

| Risk | Mitigation |
|------|-----------|
| QGIS's Python is conda-forge Python | Build the .so against the same Python version |
| ABI compatibility across QGIS versions | PyO3 modules only use bytes/numbers — no QGIS ABI dependency |
| Distribution via QGIS plugin repo | Plugin repo accepts binary wheels; ship per-platform |
| Users without Rust toolchain | They don't need it — plugin ships pre-compiled .so |
