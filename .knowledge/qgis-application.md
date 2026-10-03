---
type: Concept
title: QGIS Application Lifecycle
description: QgsApplication initialization and owner-thread shutdown in the RFC 19 native manager.
status: stable
tags: [qgis, application, lifecycle, qt, native-manager]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
sources:
  - id: qgis-api
    resource: https://api.qgis.org/api/classQgsApplication.html
    title: "QgsApplication Class Reference — QGIS API Documentation"
---

# QGIS Application Lifecycle

The native manager owns the standalone QGIS application. `app_init` is the only
operation accepted before initialization. It starts one dedicated owner thread,
creates the `QApplication`, sets the QGIS prefix, and calls
`QgsApplication::initQgis()` there. All later QGIS calls, including layer
construction and destruction, run on that same thread.

The manager keeps a narrow declaration of `QgsApplication` rather than
including `qgsapplication.h`, because some conda-forge builds trigger a static
initializer from that header during startup. This is an implementation detail
inside `manager.cpp`, not a public per-class shim.

`app_shutdown` clears the registry and owned `QgsVectorLayer` objects on the
owner thread, calls `QgsApplication::exitQgis()`, and reports the number of
released layers. The process-lifetime host intentionally keeps the
`QApplication` allocation from being destructed after QGIS plugin teardown;
this avoids the known Qt/QGIS shutdown-order crash. The shutdown integration
test leaves a layer open and asserts that the manager releases it before exit.

The C ABI remains three functions:

```c
char *qgis_invoke(const char *request_json) noexcept;
void qgis_free(char *response_json) noexcept;
unsigned qgis_transport_version(void) noexcept;
```

The Rust adapter copies request text into the ABI call and always releases the
returned response with its paired `qgis_free`. No `QApplication`, `QgsApplication`,
or other QGIS pointer is exposed to a caller.
