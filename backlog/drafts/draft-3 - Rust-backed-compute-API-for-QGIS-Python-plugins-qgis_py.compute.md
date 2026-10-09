---
id: DRAFT-3
title: Rust-backed compute API for QGIS Python plugins (qgis_py.compute)
status: Draft
assignee: []
created_date: '2026-10-09 21:14'
updated_date: '2026-10-09 21:22'
labels:
  - qgis-py
  - compute
  - performance
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: give QGIS Python plugin developers a first-class API, imported as qgis_py, that offloads computation-heavy geoprocessing to Rust. Plugin authors call idiomatic Python and never touch Rust, cargo, or FFI. This is not plugin authoring in Rust.

Naming: the distribution is qgis-py (module qgis_py), per the rename decision. qgis-rs remains only as the deprecated alias.

Architecture (revised):
- Pure Rust compute crate in py-packages/qgis-sdk/src-rust/ (crate qgis-compute). It has no QGIS, PyO3, or qgis-engine dependency. Inputs are plain in-memory data: raster bands as typed slices with a geotransform, points and geometries as coordinate arrays, feature attributes as typed columns. Outputs are the same kinds of data. Its algorithms (focal statistics, band algebra, reclassify, spatial join index, k-NN, simplification, graph routing, ground classification) are plain Rust with rayon for parallelism.
- Because it is pure Rust, the algorithms are testable with cargo test and need no QGIS installation. The crate contains no Python code and no PyO3 types.
- The QGIS adapter is separate. Layer reads and writes happen through the native QGIS manager in qgis-sys, and results come back as buffers. PyO3 bindings for the public Python API live in qgis-py (qgis_py._core), not in the pure crate, so the plugin-facing extension stays the only place that touches Python.
- Non-goals for the first cut: plugin authoring in Rust; ONNX or random-forest inference; dense 1M x 1M distance matrices (use k-nearest-neighbour queries instead).

Blocking decisions (write them down before any code):
1. Placement conflict. The repo rule is that the plugin has no runtime dependency on qgis-sdk, and qgis-sdk is dev-only and not in the plugin zip. A compute crate that runtime code depends on cannot sit inside qgis-sdk without breaking that rule. Options: (a) keep the crate at py-packages/qgis-sdk/src-rust/ and publish it as its own crate that qgis-py depends on, so qgis-sdk stays dev-only; (b) put it in a neutral location such as crates/qgis-compute. The current qgis-sdk Rust is crates/qgis-sdk, and the convention for binding Rust is <package>/src-rust/. Choose one before slice 1.
2. Transport. The engine exposes one invoke(json) seam (D09). Options: (a) add compute operations to the closed operation list in qgis-protocol, which keeps one seam but serialises all data; (b) a second, documented in-process seam for bulk buffers. Decide in writing first.
3. QGIS object bridging. Native QGIS objects (QgsVectorLayer, QgsRasterLayer, QgsProcessingFeedback) come from PyQGIS, a separately built extension. Passing sip-unwrapped pointers into qgis_py._core needs a check that both extensions link the same QGIS library instance. Per-QGIS-version validation is required.
4. Boundaries. A new crate needs an update to the D13 boundary rules, which xtask check-boundaries enforces. The enforcement must cover the pure-crate rule: no QGIS, PyO3, or engine dependency.

Feedback and cancellation: QgsProcessingFeedback is Python-side. Rust must not call into it without the GIL. Rust polls an atomic cancel flag, and the Python wrapper copies feedback.isCanceled() into that flag and reports progress at intervals. Long Rust work releases the GIL (py.allow_threads), so the QGIS UI stays responsive.

Priority (one slice each, each stops for review):
- Slice 1 (PoC): focal_mean (raster) and spatial_join (vector), end to end, with feedback support.
- Slice 2: band_algebra and reclassify; nearest_neighbor and simplify.
- Slice 3: network graph (build_graph, shortest_path, od_matrix, isochrone).
- Slice 4: point cloud (classify_ground, canopy_height_model, thin).
- Slice 5: polygonize, contour, isoband.

Performance: the numbers below are hypotheses. Each slice records a baseline on the same machine against the best existing QGIS or numpy or Shapely route, then sets the target from that baseline.
- focal_mean 5x5 on 20k x 20k raster
- spatial_join on 500k polygons
- k-NN (k=5) for 1M points
- shortest_path on a 2M-edge graph with 10k pairs
- ground classification on 50M points

Dependencies: rayon, SIMD helpers, and any geometry, raster, or point-cloud libraries are new dependencies. Each needs explicit approval before it is added.

Packaging risks: the qgis-py wheel already bundles repaired QGIS and Qt libraries (about 121 MB measured), so the size will grow. pip install must target the QGIS Python interpreter. Cancel and GIL behaviour must be tested with real QGIS, not only a fake feedback object.

Acceptance (PoC, slice 1):
- The pure crate builds and its tests run with cargo test, with no QGIS installed, and the crate has no QGIS, PyO3, or engine dependency.
- focal_mean and spatial_join accept native QgsRasterLayer and QgsVectorLayer objects with no manual conversion.
- Progress and cancellation work through QgsProcessingFeedback, and a cancelled run returns promptly.
- Speedup over the best existing Python route is measured and recorded, with the target set from that measurement.
- Installable into the QGIS Python environment (pip install qgis-py).
- Positive tests in the pytest suite, and gates pass.
- The decisions in items 1-4 are written down before the first code commit.

Later acceptance: public docstrings and examples for each module; a reproducible benchmark suite, nightly rather than per PR; a getting-started page for plugin developers with no Rust knowledge.

Hard constraint: if a plugin developer has to think about lifetimes, pointers, or cargo, the API has failed.
<!-- SECTION:DESCRIPTION:END -->
