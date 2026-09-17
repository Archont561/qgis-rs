---
type: Decision
id: D08
title: Standalone Rust App with Embedded QGIS Rendering
description: "Embed QGIS as a headless rendering engine — only 6 types needed, waitForFinished() eliminates signals."
status: draft
tags: [standalone, rendering, application, architecture]
date: 2026-09-17T00:00:00Z
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# D08: Standalone Rust App with Embedded QGIS

## The Question

Can you build a Rust application that uses QGIS as an embedded library — not as a plugin, not as a binding for general use, but as a **rendering engine**?

**Yes.** And the scope is much narrower than the original qgis-rs vision.

## What QGIS Provides That Nothing Else Can

| Capability | Rust alternative exists? |
|-----------|------------------------|
| Render a .qgs project with full styling | **No** — this is unique |
| QGIS symbology (graduated, categorized, rule-based, SVG markers) | **No** |
| Label placement engine | **No** (mapnik-rs is abandoned) |
| Print layouts | **No** |
| Expression-based rendering | **No** |
| Data access (OGR) | Yes — `gdal` |
| Geometry ops | Yes — `geo` / `geos` |
| CRS transforms | Yes — `proj` |

**The only reason to embed QGIS in Rust is map rendering with QGIS styling.**

## The Rendering Pipeline

QGIS's headless rendering uses exactly 5 types:

```
QgsApplication    → lifecycle (init/exit)          [already bound]
QgsProject        → load .qgs/.qgz project files
QgsMapSettings    → configure extent, size, DPI, CRS
QgsMapRendererSequentialJob → render synchronously
QImage            → extract PNG/JPEG bytes
```

The critical insight: **`QgsMapRendererSequentialJob::waitForFinished()` is synchronous.** No signals needed. The rendering pipeline is:

```rust
let app = Application::init()?;
let project = Project::read("map.qgs")?;
let settings = MapSettings::from_project(&project)
    .with_extent(Rect::new(14.0, 50.0, 15.0, 51.0))
    .with_size(256, 256)
    .with_dpi(96);
let image = settings.render()?;  // blocks until done
let png_bytes: Vec<u8> = image.to_png()?;
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Rust Application                    │
│                                                  │
│  ┌──────────┐   ┌──────────┐   ┌────────────┐  │
│  │ axum     │   │ CLI      │   │ egui/tauri │  │
│  │ (HTTP)   │   │ (batch)  │   │ (desktop)  │  │
│  └────┬─────┘   └────┬─────┘   └──────┬─────┘  │
│       │               │                │         │
│  ┌────▼───────────────▼────────────────▼─────┐  │
│  │           qgis-render (safe crate)         │  │
│  │   RenderBuilder → MapSettings → Image      │  │
│  │   Project::read() → Layers → Styling       │  │
│  └────────────────────┬───────────────────────┘  │
│                       │                          │
│  ┌────────────────────▼───────────────────────┐  │
│  │           qgis-sys (CXX FFI)               │  │
│  │   QgsApplication, QgsProject,              │  │
│  │   QgsMapSettings, QgsMapRendererJob,       │  │
│  │   QImage                                   │  │
│  └────────────────────┬───────────────────────┘  │
│                       │                          │
│  ┌────────────────────▼───────────────────────┐  │
│  │         libqgis_core.so (conda-forge)      │  │
│  └────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Three Product Shapes

### 1. Map Tile Server

```rust
use axum::{Router, extract::Path, response::IntoResponse};

async fn tile(
    Path((z, x, y)): Path<(u32, u32, u32)>,
) -> impl IntoResponse {
    let extent = tile_to_extent(z, x, y);
    let image = RenderBuilder::new()
        .project("map.qgs")
        .extent(extent)
        .size(256, 256)
        .render()
        .await;
    ([(CONTENT_TYPE, "image/png")], image.to_png())
}

#[tokio::main]
async fn main() {
    let app = Router::new().route("/tiles/:z/:x/:y.png", get(tile));
    axum::serve(listener, app).await;
}
```

Renders QGIS-styled map tiles over HTTP. 10x faster than QGIS Server (Python/CGI), single binary deployment.

### 2. Batch Renderer (CLI)

```bash
qgis-render --project map.qgs \
            --extent 14.0,50.0,15.0,51.0 \
            --size 4096,4096 \
            --dpi 300 \
            --output map.png
```

Generate high-resolution map images from QGIS projects. Useful for CI/CD, automated report generation, print-on-demand.

### 3. Embedded Library

```rust
use qgis_render::{Application, RenderBuilder};

let _app = Application::init()?;
let png = RenderBuilder::new()
    .project("styled_map.qgs")
    .extent(Rect::from_wsen(14.0, 50.0, 15.0, 51.0))
    .size(1024, 1024)
    .render()?
    .to_png()?;
```

Embed QGIS rendering in any Rust application — desktop apps, microservices, Lambda functions.

## Types to Bind (~6 total)

| Type | FFI Functions Needed | Notes |
|------|---------------------|-------|
| `QgsApplication` | 3 (new, init, exit) | ✅ Already bound |
| `QgsProject` | 4 (new, read, instance, layers) | Medium |
| `QgsMapSettings` | 8 (set layers, extent, size, DPI, CRS, flags, etc.) | Medium |
| `QgsMapRendererSequentialJob` | 4 (new, start, waitForFinished, renderedImage) | Easy |
| `QImage` | 3 (width, height, to_png_bytes) | Easy |
| `QgsVectorLayer` | 6 (already bound + add to settings) | ✅ Mostly bound |

**Total: ~28 FFI functions.** Achievable in weeks, not years.

## The Signal Problem — Solved

`QgsMapRendererSequentialJob` has two modes:
1. **Async**: `start()` + connect to `finished()` signal → needs Qt event loop
2. **Sync**: `start()` + `waitForFinished()` → **blocks until done, no signals**

For a Rust app, the sync mode is perfect:

```cpp
// In the shim:
::std::unique_ptr<QImageHandle> map_render(QgsMapSettingsHandle& settings) noexcept {
    try {
        auto job = QgsMapRendererSequentialJob(*real_settings(settings));
        job.start();
        job.waitForFinished();  // blocks — no signals needed
        QImage img = job.renderedImage();
        return ::std::make_unique<QImageHandle>(new QImage(img));
    } catch (...) {
        return nullptr;
    }
}
```

The Qt event loop still runs internally (QGIS needs it for provider I/O), but Rust doesn't need to interact with it. `QT_QPA_PLATFORM=offscreen` handles the display requirement.

## Macro Ideas for This Scope

At ~6 types and ~28 FFI functions, macros aren't necessary. But one macro would help the **safe wrapper**:

### RenderBuilder derive

```rust
#[derive(RenderConfig)]
struct TileRender {
    #[qgis(map_setting = "setExtent")]
    extent: Rect,
    #[qgis(map_setting = "setOutputSize")]
    size: (u32, u32),
    #[qgis(map_setting = "setDpi", default = 96.0)]
    dpi: f64,
    #[qgis(map_setting = "setDestinationCrs")]
    crs: Option<String>,
}
```

Generates the builder pattern and the FFI calls to configure `QgsMapSettings`. But honestly, at 6 types, writing this by hand is faster.

## What the Existing qgis-sys Infrastructure Gives You

| Existing artifact | Use for rendering app? |
|-------------------|----------------------|
| `crates/qgis-sys/` | ✅ Keep — add ~4 new types |
| Handle macros | ✅ Keep — reuse for new types |
| `convert.h` | ✅ Keep — string conversion still needed |
| Scaffold task | ✅ Keep — use for new types |
| Build system (build.rs) | ✅ Keep — already links libqgis_core |
| pixi environment | ✅ Keep — provides QGIS + Qt |
| pixi-sandbox provisioning | ✅ Keep — for CI and sandbox builds |
| Test infrastructure | ✅ Keep — add rendering tests |

**The existing qgis-rs infrastructure is actually well-suited for this.** The pivot isn't "abandon qgis-sys" — it's "focus qgis-sys on rendering."

## Comparison: Three Paths

| | D07: Rust Plugins | D08: Standalone App | Both |
|---|---|---|---|
| Bridge | PyO3 (Python↔Rust) | CXX (C++↔Rust) | Both bridges |
| QGIS dependency | User's QGIS install | Bundled (conda-forge) | Both |
| Rendering | ❌ (Python handles it) | ✅ (embedded) | ✅ |
| Computation speed | ✅ (Rust engine) | ✅ (native) | ✅ |
| Distribution | QGIS plugin repo | Single binary / Docker | Both |
| Effort | ~2 weeks per algorithm | ~4 weeks for rendering | ~6 weeks |
| Market | QGIS users (millions) | DevOps / SaaS | Both |

## Recommendation

**Start with D08 (standalone rendering app).** It:
1. Uses the existing qgis-sys infrastructure (not wasted effort)
2. Fills a real gap (no good headless QGIS renderer in Rust)
3. Has a clear product shape (tile server, CLI, library)
4. Requires only ~6 types and ~28 FFI functions
5. Avoids the signal/slot problem entirely (waitForFinished)
6. Can later add D07 (Processing plugins) as a second product
