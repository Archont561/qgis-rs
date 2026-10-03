---
id: TASK-25.1
title: 'RFC 19 phase 2: native manager, ID registry and lifecycle behind qgis_invoke'
status: Done
assignee: []
created_date: '2026-10-02 23:23'
updated_date: '2026-10-03 18:08'
labels:
  - rfc
  - ffi
  - cpp
milestone: m-0
dependencies:
  - TASK-25.4
  - TASK-24
references:
  - 'https://github.com/Archont561/qgis-rs/issues/19'
documentation:
  - .knowledge/architecture.md
  - .knowledge/build-system.md
  - .knowledge/decisions/D09-wire-protocol-over-ffi.md
  - .knowledge/decisions/D12-qgis-native-manager-over-c-abi.md
  - .knowledge/decisions/INDEX.md
  - >-
    backlog/docs/architecture/doc-4 -
    QGIS-Native-Manager-and-API-Coverage-Strategy.md
parent_task_id: TASK-25
priority: high
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Phase 2 of RFC 19. Stand the native manager up next to the existing cxx bridge and move the two shims that already exist onto it, so the boundary is proven before any new QGIS feature depends on it.

Scope: one manager translation unit under crates/qgis-sys that includes qgs*.h and nothing else does; qgis_invoke, qgis_free and qgis_transport_version as the only default-visible symbols; QJsonDocument for the envelope on the C++ side; a catch(...) fence before every return out of extern "C"; an ID registry holding QHash<id, std::unique_ptr<T>> so no QGIS pointer crosses the boundary; the serialisation happening inside qgis_invoke, per ADR D12 (with D05's QGIS thread-affinity invariant). On the Rust side, the extern "C" declarations, a String round-trip helper that always pairs qgis_free with the pointer it got, and the router forwarding app.init, engine.info and the current vector layer operations.

The gated suite is the acceptance surface: tests/application_lifecycle.rs and tests/vector_layer.rs already exercise a real QgsApplication and a real vector layer, and both pass headless in the sandbox today. They must keep passing through the manager, with the same QT_QPA_PLATFORM=offscreen and single-threaded harness.

Decide the concurrency model before writing the mutex: one global lock around qgis_invoke is the smaller change, a dedicated QGIS thread with a request queue is what QGIS itself prefers for anything touching QgsApplication. Whichever is chosen is the thing the phase has to document.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A single manager translation unit is the only file in the repository that includes qgs headers
- [x] #2 qgis_invoke, qgis_free and qgis_transport_version are the only default-visible symbols, with -fvisibility=hidden set for the C++ unit
- [x] #3 Every extern C function has a catch-all fence and returns an error envelope instead of propagating an exception, returning null or aborting
- [x] #4 Live QGIS objects are held in an ID registry keyed by integer id, and no raw pointer appears on the wire
- [x] #5 app.init, engine.info and the existing vector layer operations are served by the manager, and the gated tests application_lifecycle and vector_layer pass headless through it
- [x] #6 The chosen concurrency model, one global mutex or a dedicated QGIS thread, is implemented and documented in the ADR from the parent task
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03: Started implementation after TASK-25.4 and TASK-24 completed. The implementation will use the D12 dedicated owner thread and queue, the qgis-protocol transport envelope, opaque generational object IDs, and the three-symbol C ABI.

2026-10-03: Added the native manager C ABI in crates/qgis-sys/src/native_manager/manager.cpp. It is the sole QGIS-header-owning translation unit; legacy CXX compatibility functions now live there and their former shim files contain no QGIS includes.

2026-10-03: Added qgis_invoke, qgis_free, and qgis_transport_version with default visibility opt-in over -fvisibility=hidden. The Rust invoke wrapper copies request text and always releases the exact response pointer with qgis_free.

2026-10-03: Implemented the dedicated owner thread and blocking request queue, app_init and engine_info, integer layer IDs with unique_ptr ownership, vector-layer metadata operations, structured error envelopes, and concurrent-caller coverage.

2026-10-03: Verification passed: serialized qgis-sys tests (5 application-info, 1 lifecycle, 5 native-manager, 6 vector-layer), qgis-protocol tests, qgis-engine tests, cargo clippy with -D warnings, check-cpp, clang-tidy, and readelf confirmed only the three C ABI exports have DEFAULT visibility in manager.o. Expected QGIS/PDAL/fontconfig warnings remain.

2026-10-03: Full pixi run gates reached the repository lint and format stages, then stopped in qgis-rs build because the bun environment could not fetch crates.io config for anyhow due repeated TLS unexpected EOF errors. This is an environment network blocker; focused Rust/C++ verification for this task remains green.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
RFC 19 phase 2 is implemented. The native manager owns QGIS access on one executor thread, exposes only the three C ABI symbols, serializes JSON requests and responses, keeps QGIS objects behind integer IDs, and routes app lifecycle and existing vector-layer operations through the manager. Repository documentation and protocol vocabulary were updated, and the acceptance suite is green.
<!-- SECTION:FINAL_SUMMARY:END -->
