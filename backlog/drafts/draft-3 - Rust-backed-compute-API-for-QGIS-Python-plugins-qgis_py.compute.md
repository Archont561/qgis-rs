---
id: DRAFT-3
title: Rust-backed compute API for QGIS Python plugins (qgis_py.compute)
status: Draft
assignee: []
created_date: '2026-10-09 21:14'
labels:
  - qgis-py
  - compute
  - performance
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: give QGIS Python plugin developers a first-class API, imported as qgis_py, that offloads computation-heavy geoprocessing to Rust. Plugin authors call idiomatic Python and never touch Rust, cargo, or FFI. This is not plugin authoring in Rust.

Naming: the distribution is qgis-py (module qgis_py), per the rename decision. qgis-rs remains only as the deprecated alias. The Python-facing code lives in py-packages/qgis-py.

Non-goals for the first cut: plugin authoring in Rust; ONNX or random-forest inference; dense 1M x 1M distance matrices (use k-nearest-neighbour queries instead).

Seams first (blocking, decide before any code):
1. Transport. The engine exposes one invoke(json) seam (D09). Options: (a) add compute operations to the closed operation list in qgis-protocol, which keeps one seam but serialises all data; (b) a second, explicitly documented in-process seam for bulk data (numpy-style buffers or pointers) that must not bypass the protocol silently. Recommend deciding (a) or (b) in writing first.
2. QGIS object bridging. Native QGIS objects (QgsVectorLayer, QgsRasterLayer, QgsProcessingFeedback) come from PyQGIS, a separately built extension. Passing sip-unwrapped pointers into qgis_py._core needs a check that both extensions link the same QGIS library instance. Per-QGIS-version validation is required.
3. Layer data access goes through the native QGIS manager in qgis-sys, not qgis-sdk. qgis-sdk is the plugin-authoring SDK and has no runtime role.
4. Crate layout. A new qgis-compute crate conflicts with the approved meta-crate feature flags (render, server, styles, cli). Recommended default: a compute feature on the qgis-rs meta crate, with the code under crates/qgis-compute as a module. Needs approval.

Feedback and cancellation: QgsProcessingFeedback is Python-side. Rust must not call into it without the GIL. Rust polls an atomic cancel flag, and the Python wrapper copies feedback.isCanceled() into that flag and reports progress at intervals. Long Rust work releases the GIL (py.allow_threads), so the QGIS UI stays responsive.

Priority (one slice each, each stops for review):
- Slice 1 (PoC): focal_mean (raster) and spatial_join (vector), end to end, with feedback support.
- Slice 2: band_algebra and reclassify; nearest_neighbor and simplify.
- Slice 3: network graph (build_graph, shortest_path, od_matrix, isochrone).
- Slice 4: point cloud (classify_ground, canopy_height_model, thin).
- Slice 5: polygonize, contour, isoband.

Performance: the numbers below are hypotheses. Each slice first records a baseline on the same machine against the best existing QGIS or numpy or Shapely route, then sets the target from that baseline. A "numpy falls off a cliff" claim is not evidence.
- focal_mean 5x5 on 20k x 20k raster
- spatial_join on 500k polygons
- k-NN (k=5) for 1M points
- shortest_path on a 2M-edge graph with 10k pairs
- ground classification on 50M points

Dependencies: rayon, SIMD helpers, and point-cloud or raster libraries are new dependencies. Each needs explicit approval before it is added. The no-new-dependency rule applies.

Packaging risks: the qgis-py wheel already bundles repaired QGIS and Qt libraries (about 121 MB measured), so the size will grow. pip install must target the QGIS Python interpreter. The cancel and GIL behaviour must be tested with real QGIS, not only a fake feedback.

Acceptance (PoC, slice 1):
- focal_mean and spatial_join accept native QgsRasterLayer and QgsVectorLayer objects with no manual conversion.
- Progress and cancellation work through QgsProcessingFeedback, and a cancelled run returns promptly.
- Speedup over the best existing Python route is measured and recorded, with the target set from that measurement.
- Installable into the QGIS Python environment (pip install qgis-py).
- Positive tests in the pytest suite, and gates pass.
- The seams decision in items 1-4 is written down before the first code commit.

Later acceptance: public docstrings and examples for each module; a reproducible benchmark suite, nightly rather than per PR; a getting-started page for plugin developers with no Rust knowledge.

Hard constraint: if a plugin developer has to think about lifetimes, pointers, or cargo, the API has failed.
<!-- SECTION:DESCRIPTION:END -->
