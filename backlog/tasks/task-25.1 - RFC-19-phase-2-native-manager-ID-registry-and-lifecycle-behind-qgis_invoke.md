---
id: TASK-25.1
title: 'RFC 19 phase 2: native manager, ID registry and lifecycle behind qgis_invoke'
status: To Do
assignee: []
created_date: '2026-10-02 23:23'
updated_date: '2026-10-03 02:16'
labels:
  - rfc
  - ffi
  - cpp
dependencies:
  - TASK-25.4
references:
  - 'https://github.com/Archont561/qgis-rs/issues/19'
parent_task_id: TASK-25
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Phase 2 of RFC 19. Stand the native manager up next to the existing cxx bridge and move the two shims that already exist onto it, so the boundary is proven before any new QGIS feature depends on it.

Scope: one manager translation unit under crates/qgis-sys that includes qgs*.h and nothing else does; qgis_invoke, qgis_free and qgis_transport_version as the only default-visible symbols; QJsonDocument for the envelope on the C++ side; a catch(...) fence before every return out of extern "C"; an ID registry holding QHash<id, std::unique_ptr<T>> so no QGIS pointer crosses the boundary; the serialisation happening inside qgis_invoke, per ADR D05. On the Rust side, the extern "C" declarations, a String round-trip helper that always pairs qgis_free with the pointer it got, and the router forwarding app.init, engine.info and the current vector layer operations.

The gated suite is the acceptance surface: tests/application_lifecycle.rs and tests/vector_layer.rs already exercise a real QgsApplication and a real vector layer, and both pass headless in the sandbox today. They must keep passing through the manager, with the same QT_QPA_PLATFORM=offscreen and single-threaded harness.

Decide the concurrency model before writing the mutex: one global lock around qgis_invoke is the smaller change, a dedicated QGIS thread with a request queue is what QGIS itself prefers for anything touching QgsApplication. Whichever is chosen is the thing the phase has to document.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A single manager translation unit is the only file in the repository that includes qgs headers
- [ ] #2 qgis_invoke, qgis_free and qgis_transport_version are the only default-visible symbols, with -fvisibility=hidden set for the C++ unit
- [ ] #3 Every extern C function has a catch-all fence and returns an error envelope instead of propagating an exception, returning null or aborting
- [ ] #4 Live QGIS objects are held in an ID registry keyed by integer id, and no raw pointer appears on the wire
- [ ] #5 app.init, engine.info and the existing vector layer operations are served by the manager, and the gated tests application_lifecycle and vector_layer pass headless through it
- [ ] #6 The chosen concurrency model, one global mutex or a dedicated QGIS thread, is implemented and documented in the ADR from the parent task
<!-- AC:END -->
