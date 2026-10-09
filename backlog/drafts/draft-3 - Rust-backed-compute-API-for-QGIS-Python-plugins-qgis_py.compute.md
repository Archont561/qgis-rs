---
id: DRAFT-3
title: Rust-backed compute API for QGIS Python plugins (qgis_py.compute)
status: Draft
assignee: []
created_date: '2026-10-09 21:14'
updated_date: '2026-10-09 21:34'
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

Crate layout:
- crates/qgis-compute: pure Rust compute library (crate qgis-compute). No QGIS, PyO3, C ABI, or qgis-engine dependency. Inputs are plain in-memory data: raster bands as typed slices with a geotransform, coordinate arrays for points and geometries, typed attribute columns. Algorithms: focal statistics, band algebra, reclassify, spatial join index, k-NN, simplification, graph routing, ground classification. rayon for parallelism.
- crates/qgis-compute-ffi: C ABI cdylib over qgis-compute. Only extern "C" functions, a generated C header, and buffer-in/buffer-out signatures. Every entry point wraps its body in catch_unwind so a Rust panic never unwinds into the caller. The caller owns all buffers, and the library never retains pointers after a call returns.
- qgis_py._core (PyO3, in py-packages/qgis-py/src-rust): depends directly on qgis-compute for the runtime API. It does not go through the C ABI.

Packaging and the optional extra for qgis-sdk:
- qgis-sdk stays a pure Python package with no required Rust dependency. Its base install works without any native library.
- qgis-sdk[accel] is an optional extra that ships the qgis-compute-ffi shared library per platform.
- qgis-sdk loads that library at runtime with ctypes. Numeric kernels take numpy arrays through the buffer protocol. If the library is missing, or its version does not match, qgis-sdk uses the pure Python implementation and records which path it took.
- No QGIS objects cross the C ABI. Layers, feedback, and project state stay in PyQGIS. Only numeric buffers and scalar parameters cross.
- The ctypes route avoids tying the library to one CPython ABI. This is the coupling D13 forbids, so the choice is deliberate.

Boundaries (to add to D13 and enforce in xtask check-boundaries):
- qgis-compute depends on nothing in the workspace.
- qgis-compute-ffi depends only on qgis-compute.
- qgis_py._core -> qgis-compute is allowed.
- qgis-sdk -> qgis-compute-ffi is a runtime, optional, ctypes edge. It is not a Cargo edge and must not appear in any Cargo.toml.
- qgis-rs (meta crate) may depend on qgis-compute behind a compute feature, which needs approval.

Blocking decisions (write them down before any code):
1. Build tooling for the C header: cbindgen, or a hand-written header checked by a test. cbindgen is a new build dependency and needs approval.
2. Native library distribution: which platforms, how the library is staged into the qgis-sdk wheel, and how the optional extra is named and published.
3. Relationship to the open qgis-sdk crate removal. This plan works whether or not crates/qgis-sdk is removed, but the packaging steps depend on that answer.
4. QGIS object bridging for qgis_py._core. Passing sip-unwrapped pointers into qgis_py._core needs a check that both extensions link the same QGIS library instance. Per-QGIS-version validation is required.

Parity: for every kernel, the native and pure Python paths must produce the same result on the same fixtures. A kernel without a parity test does not ship.

Feedback and cancellation: QgsProcessingFeedback is Python-side. Rust must not call into it without the GIL. Rust polls an atomic cancel flag, and the Python wrapper copies feedback.isCanceled() into that flag and reports progress at intervals. Long Rust work releases the GIL (py.allow_threads), so the QGIS UI stays responsive.

Priority (one slice each, each stops for review):
- Slice 1 (PoC): focal_mean (raster) and spatial_join (vector), end to end, with feedback support, pure Rust core, qgis_py binding, and the ctypes path for qgis-sdk[accel].
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

Dependencies: rayon, SIMD helpers, geometry, raster, and point-cloud libraries, and cbindgen, are new dependencies. Each needs explicit approval before it is added.

Packaging risks: the qgis-py wheel already bundles repaired QGIS and Qt libraries (about 121 MB measured), so the size will grow. pip install must target the QGIS Python interpreter. The optional native library adds per-platform size to qgis-sdk[accel]. Cancel and GIL behaviour must be tested with real QGIS, not only a fake feedback object.

Acceptance (PoC, slice 1):
- qgis-compute builds and its tests run with cargo test, with no QGIS installed. It has no QGIS, PyO3, C ABI, or engine dependency.
- qgis-compute-ffi exposes the C header, and a test calls it through ctypes and checks the result against qgis-compute.
- focal_mean and spatial_join accept native QgsRasterLayer and QgsVectorLayer objects with no manual conversion.
- qgis-sdk works with and without the native library, with identical results on the parity fixtures.
- Progress and cancellation work through QgsProcessingFeedback, and a cancelled run returns promptly.
- Speedup over the best existing Python route is measured and recorded, with the target set from that measurement.
- Installable into the QGIS Python environment (pip install qgis-py), and qgis-sdk[accel] installs where a platform build exists.
- Positive tests in the pytest suite, and gates pass.
- The decisions in items 1-4 are written down before the first code commit.

Later acceptance: public docstrings and examples for each module; a reproducible benchmark suite, nightly rather than per PR; a getting-started page for plugin developers with no Rust knowledge.

Hard constraint: if a plugin developer has to think about lifetimes, pointers, or cargo, the API has failed.
<!-- SECTION:DESCRIPTION:END -->
