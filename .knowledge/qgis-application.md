---
type: Concept
title: QGIS Application Lifecycle
description: QgsApplication initialization, the QApplication workaround, and RAII patterns.
status: stable
tags: [qgis, application, lifecycle, qt]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
sources:
  - id: qgis-api
    resource: https://api.qgis.org/api/classQgsApplication.html
    title: "QgsApplication Class Reference — QGIS API Documentation"
  - id: qgis-cpp-standalone
    resource: https://gis.stackexchange.com/questions/124542
    title: "How to develop C++ standalone QGIS C++ Application"

---

# QGIS Application Lifecycle

## The Problem

QGIS requires `QgsApplication::initQgis()` before any QGIS API call, and `QgsApplication::exitQgis()` before process exit. In C++, this is straightforward:

```cpp
QgsApplication app(argc, argv, true);
QgsApplication::setPrefixPath("/usr", true);
QgsApplication::initQgis();
// ... use QGIS ...
QgsApplication::exitQgis();
```

## The Workaround

The shim in `app.cpp` **does not use `QgsApplication` directly**. Instead it creates a `QApplication` and calls `QgsApplication` static methods via a forward-declared class:

```cpp
class QgsApplication {
  public:
    static void setPrefixPath(const QString&, bool);
    static QString prefixPath();
    static void initQgis();
    static void exitQgis();
};
```

**Why?** Including `<qgsapplication.h>` triggers a static initializer in `qgssettingsentry.h` that crashes on some conda-forge builds. By avoiding the header entirely and using a minimal forward declaration, the shim sidesteps this issue.

The actual `void*` inside the handle is a `QApplication*`, not a `QgsApplication*`:

```cpp
auto* app = new QApplication(s_argc, s_argv);
return ::std::make_unique<qgis_shim::core::QgsApplication>(
    static_cast<void*>(app));
```

## Application Info

`application_info()` returns a shared struct with QGIS version, Qt version, and OS platform. This struct is defined in the bridge:

```rust
#[derive(Debug)]
pub struct AppInfo {
    pub version: String,
    pub qt_version: String,
    pub platform: String,
}
```

This function does NOT require application initialization — it reads compile-time constants and `QSysInfo`.

## RAII Pattern (Rust Side)

Tests use `AppHandle` for deterministic init/exit:

```rust
pub struct AppHandle {
    inner: cxx::UniquePtr<app_ffi::QgsApplication>,
}

impl AppHandle {
    pub fn new() -> Self {
        let prefix = std::env::var("CONDA_PREFIX").unwrap_or_default();
        let mut inner = app_ffi::application_new(&prefix);
        assert!(!inner.is_null());
        app_ffi::application_init_qgis(inner.pin_mut());
        Self { inner }
    }
}

impl Drop for AppHandle {
    fn drop(&mut self) {
        if !self.inner.is_null() {
            app_ffi::application_exit_qgis(self.inner.pin_mut());
        }
    }
}
```

## Test Implications

- Tests that need QGIS must create an `AppHandle` first: `let _app = helpers::AppHandle::new();`
- Tests must run with `--test-threads=1` because `QApplication` is a process-wide singleton
- `QT_QPA_PLATFORM=offscreen` prevents Qt from trying to open a display
- The `setup` task creates a symlink workaround for `libqca-qt5` → `libqca-qt6`
