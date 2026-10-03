---
id: doc-8
type: specification
title: "Proposition: A Future Standalone Pure-Rust QGIS Project Renderer"
description: "A reviewable proposal for importing a declared QGIS project subset into a deterministic, headless, pure-Rust rendering pipeline."
tags: [proposition, rendering, qgis-project, qgs, qgz, qml, rust, compatibility]
status: proposed
created_date: '2026-10-03'
---

# Proposition: A Future Standalone Pure-Rust QGIS Project Renderer

## Status and intent

This is a proposition for review, not an accepted implementation commitment. It should be validated with a real QGIS-generated project corpus before production renderer work begins.

The proposition is:

> Build a deterministic, headless, pure-Rust renderer that imports a declared, version-pinned subset of QGS/QGZ/QML into a normalized Rust render model. Do not attempt to implement all QGIS semantics or claim complete visual parity by merely parsing project XML.

The renderer should treat QGIS project files as compatibility inputs. Its own stable boundary is a versioned intermediate representation and an explicit capability report.

Related repository work:

- [TASK-12](../../tasks/task-12%20-%20Bind-QgsMapSettings-and-QgsMapRendererSequentialJob-for-embedded-rendering.md) — native QGIS rendering baseline;
- [TASK-25.3](../../tasks/task-25.3%20-%20RFC-19-phase-4-render_map-and-export_features-against-real-QGIS.md) — native manager rendering/export;
- [TASK-30](../../tasks/task-30%20-%20Generate-a-versioned-QGIS-API-manifest-and-manager-handlers.md) — versioned QGIS API manifest;
- [doc-4](doc-4%20-%20QGIS-Native-Manager-and-API-Coverage-Strategy.md) — native manager and API coverage;
- [doc-7](doc-7%20-%20Rust-CLI-Cross-Language-FFI-and-QGIS-SDK-Product-Boundaries.md) — standalone CLI and backend boundaries.

## Why this is needed

The current `qgis-render` project model checks project paths and extensions, but project parsing, layer discovery, and rendering are not implemented. The current `qgis-styles` crate provides a useful pure-Rust style IR, but it is not yet a QML codec or a complete representation of QGIS symbology.

A pure Rust renderer would provide:

- portable headless rendering without Qt or PyQGIS;
- deterministic CI and server execution;
- a small deployable renderer for supported projects;
- reusable map rendering for CLI, HTTP, MCP, Python, and Node clients;
- a compatibility report instead of an opaque “render failed” result;
- a foundation for a future qgis-rs-native project bundle if that becomes necessary.

It would not replace the native QGIS backend. Exact QGIS provider, plugin, Processing, expression, layout, and GUI behavior remains a native-QGIS capability.

## Available QGIS format information

### QGS and QGZ

The official QGIS documentation describes QGS as XML for storing projects. It lists project title, project CRS, layer tree, snapping settings, relations, map canvas extent, project models, legends, map views, layer data sources, styles, renderers, blend modes, opacity, and project properties as project content.

QGZ is documented as a compressed ZIP archive containing a QGS file and a QGD SQLite database for auxiliary project data. The first pure-Rust profile should support filesystem QGS and QGZ only and report other project-storage backends as unsupported.

Reference: [QGIS file formats — QGS/QGZ](https://docs.qgis.org/3.44/en/docs/user_manual/appendices/qgis_file_formats.html).

### QML and QLR

QML is the QGIS XML layer-style format. It contains QGIS-rendering information such as symbols, sizes, rotations, labelling, opacity, blend mode, and renderer configuration.

QLR is an XML layer-definition format containing a data-source pointer and QGIS style information. It is a possible future input for single-layer rendering, but it is not a replacement for a project file.

Reference: [QGIS file formats — QML and QLR](https://docs.qgis.org/3.44/en/docs/user_manual/appendices/qgis_file_formats.html).

### No complete stable schema

The official project documentation says that the project format has changed several times and that older projects may not work correctly with newer QGIS versions. The documentation gives a conceptual format description and diagrams, but it does not provide a complete stable XSD for all project and provider content.

The effective executable specification is distributed across QGIS source code and API serialization hooks:

- `QgsProject::read()` and `QgsProject::write()`;
- `readProject()` and `writeProject()` XML hooks;
- per-class `readXml()` and `writeXml()` implementations;
- `QgsReadWriteContext`;
- `QgsPathResolver`;
- `QgsProjectStorage` implementations;
- provider and plugin serialization code.

References:

- [QgsProject API](https://api.qgis.org/api/classQgsProject.html)
- [QgsReadWriteContext API](https://api.qgis.org/api/classQgsReadWriteContext.html)
- [QgsPathResolver API](https://qgis.org/pyqgis/master/core/QgsPathResolver.html)
- [QgsProjectStorage API](https://www.qgis.org/pyqgis/master/core/QgsProjectStorage.html)
- [QGIS project serialization source](https://github.com/qgis/QGIS/tree/release-3_44/src/core/project)

Therefore, a Rust importer must be version-aware and must use QGIS-generated fixtures as part of its compatibility contract.

## Proposed architecture

```text
.qgs / .qgz / .qml / .qlr
        |
        v
container reader
        |
        v
version-aware XML/style importer
        |
        v
compatibility report and diagnostics
        |
        v
normalized RenderProject IR
        |
        v
data-source resolver
        |
        v
feature/raster pipeline
        |
        v
expression and filter evaluator
        |
        v
symbol and label evaluator
        |
        v
render plan / scene graph
        |
        v
raster or vector output backend
```

The importer must not render arbitrary XML nodes directly. It should normalize supported QGIS content into an IR that does not depend on Qt, QGIS C++ objects, DOM lifetimes, provider-specific C++ types, or Python callbacks.

## Proposed normalized model

```rust
pub struct RenderProject {
    pub source_format: ProjectFormat,
    pub source_version: Option<String>,
    pub title: Option<String>,
    pub crs: Crs,
    pub views: Vec<MapView>,
    pub layer_tree: LayerTree,
    pub layers: Vec<RenderLayer>,
    pub resources: ResourceTable,
    pub diagnostics: Vec<Diagnostic>,
}

pub struct MapView {
    pub id: String,
    pub extent: Extent,
    pub crs: Crs,
    pub width: u32,
    pub height: u32,
    pub dpi: f64,
    pub rotation: f64,
    pub background: Color,
}

pub struct RenderLayer {
    pub id: String,
    pub name: String,
    pub source: DataSourceRef,
    pub crs: Option<Crs>,
    pub visibility: VisibilityRule,
    pub opacity: f64,
    pub blend_mode: BlendMode,
    pub renderer: LayerRenderer,
    pub labeling: Option<Labeling>,
}
```

The exact public Rust types remain open. The important contract is that the IR is versioned, serializable where useful, diagnosable, and independent of QGIS runtime objects.

## Import and container policy

### QGS/QGZ reader

The first reader should:

- validate file and archive structure;
- enforce ZIP size, nesting, and path-traversal limits;
- locate the project XML;
- expose QGZ auxiliary data without assuming all QGD tables are understood;
- preserve unknown archive members;
- read project metadata, CRS, views, layer tree, layer IDs, source URIs, providers, visibility, opacity, blend mode, scale ranges, and style references;
- preserve unknown XML content for diagnostics or future import;
- distinguish parse success from render support.

### Path and resource resolver

QGIS projects contain relative paths, embedded resources, provider URIs, and possibly credentials or preprocessing rules. Pure mode should use an explicit resolver:

```rust
pub trait ResourceResolver {
    fn resolve_path(&self, project_path: &Path, stored: &str) -> Result<ResolvedResource>;
    fn open_resource(&self, resource: &ResolvedResource) -> Result<Box<dyn Read>>;
}
```

Initial policy:

```text
local files                 supported
relative project paths      supported
embedded QGZ resources      supported where declared
network URLs                disabled by default
database credentials        never logged or extracted
QGIS path preprocessors     unsupported in pure mode
custom provider URIs        unsupported unless registered
```

Missing data sources must produce diagnostics. The resolver must not silently select a different local file.

### Version profiles

The first profile should be pinned to the repository's target QGIS release, currently QGIS 3.44.x. Future profiles can be explicit:

```text
qgis-3.44-pure-rust
qgis-3.40-pure-rust
qgis-4.x-pure-rust
```

A profile defines supported XML elements, provider mappings, style codecs, expression functions, defaults, and known deviations.

## Initial pure-Rust rendering profile

### Project features

Initial support target:

- filesystem QGS;
- filesystem QGZ;
- project title and metadata;
- project CRS;
- map views, extents, dimensions, and rotation;
- layer-tree order and groups;
- layer visibility;
- local source references;
- layer CRS;
- layer opacity and blend mode;
- scale visibility;
- basic inline or referenced styles.

### Vector sources

Start with providers that can be implemented and tested in Rust without QGIS:

- GeoJSON;
- CSV/TSV with geometry columns;
- FlatGeobuf;
- selected GeoPackage support;
- optionally Shapefile after provider behavior is characterized.

Do not initially claim support for PostgreSQL, Oracle, WMS/WFS, ArcGIS services, arbitrary GDAL providers, or custom QGIS provider plugins.

### Raster sources

Start with:

- GeoTIFF;
- common local image formats;
- local raster resources.

Later work can add tiled reads, overviews, Cloud Optimized GeoTIFF, classification, reprojection, and raster blending.

### Vector renderers

Initial style target:

- single symbol;
- categorized renderer;
- graduated renderer;
- rule-based renderer;
- simple marker, line, and fill symbol layers;
- opacity and outlines;
- dash patterns;
- scale ranges;
- a small declared set of data-defined properties.

QML import should be a versioned codec into the Rust style IR. The current `qgis-styles` model is a seed, not evidence of complete QML compatibility. Raw unsupported QML may be preserved for diagnostics but must not be treated as executable rendering behavior.

### Expressions

The first expression profile should be a documented subset:

```text
field references
literals
arithmetic
comparison
boolean operators
selected string functions
selected numeric functions
```

The pure renderer should report unsupported project scopes, custom Python functions, provider-specific functions, and plugin functions. It must not silently treat an unsupported filter as true.

### Labels and layouts

Labeling should be separate from basic symbol rendering:

1. field-based text;
2. simple placement;
3. collision avoidance;
4. data-defined text and formatting;
5. curved labels, callouts, obstacles, and advanced placement.

QGIS print layouts, atlases, reports, 3D map views, annotations, and GUI-only layout features should be separate milestones. A print layout is not merely a map render with a different image size.

## Render pipeline

```text
load RenderProject
  -> resolve data sources
  -> validate CRS and transforms
  -> select visible layers
  -> apply scale rules
  -> fetch feature/raster batches
  -> transform coordinates
  -> evaluate filters
  -> classify features
  -> build symbol draw commands
  -> place labels
  -> order layers and symbol layers
  -> rasterize or encode vector output
  -> write artifact and evidence metadata
```

Initial output target:

- PNG;
- JPEG;
- optionally WebP.

SVG, PDF, world files, georeferenced raster output, and vector tiles should follow separate capability decisions.

## Determinism and evidence

Pure rendering should support reproducible results:

- no implicit network access;
- stable feature ordering;
- fixed numeric and rounding policies;
- explicit font configuration and font identity;
- fixed encoder settings;
- explicit color-management behavior;
- deterministic placement seeds;
- stable diagnostics;
- input and renderer-profile hashes in artifact metadata.

Cross-platform font rasterization may prevent pixel-identical output. Tests should therefore combine:

- exact normalized-IR tests;
- exact draw-command and metrics tests;
- perceptual image thresholds;
- QGIS reference images generated in a pinned environment.

The existence of a screenshot is not evidence of visual correctness. Every visual check needs explicit dimensions, pixel/metric criteria, or a documented review decision.

## Compatibility levels

The renderer should report three separate levels:

### Parse compatibility

The project can be opened and inspected.

### Render compatibility

The project can render through the selected pure-Rust profile.

### Visual compatibility

The output has been compared with a pinned QGIS reference render and meets declared image criteria.

These levels must not be conflated.

Example report:

```json
{
  "project": "map.qgz",
  "qgis_project_version": "3.44.0",
  "renderer_profile": "qgis-3.44-pure-rust",
  "parse_status": "supported",
  "render_status": "partial",
  "visual_status": "not_verified",
  "layers": [
    {"id": "roads", "provider": "ogr", "status": "supported"},
    {"id": "imagery", "provider": "wms", "status": "unsupported"}
  ],
  "warnings": []
}
```

Useful CLI commands would be:

```bash
qgis-cli project inspect map.qgz --json
qgis-cli project compatibility map.qgz \
  --profile qgis-3.44-pure-rust --json
qgis-cli render map.qgz \
  --profile qgis-3.44-pure-rust \
  --reference qgis-reference.png \
  --metrics evidence.json
```

## Native project format question

Do not introduce a new qgis-rs project format during the first importer milestone.

Use three layers:

```text
QGS/QGZ       compatibility input
RenderProject normalized internal IR
future bundle optional portable deployment format
```

If a native format becomes necessary, define it separately rather than pretending to be QGS:

```text
.qrsproj/
├── manifest.json
├── project.json
├── layers/
├── styles/
├── resources/
└── data/
```

A future qgis-rs bundle could provide a stable schema, content hashes, portable resources, explicit providers, and deterministic deployment. It must not claim QGIS compatibility without a deliberate QGIS adapter.

## Proposed feasibility sequence

### Phase 0 — project corpus and format inventory

Create real QGIS fixtures for:

- empty projects;
- vector and raster layers;
- grouped layers;
- categorized, graduated, and rule-based styles;
- labels;
- joins;
- relative paths;
- QGZ with QGD;
- embedded resources;
- broken layers;
- multiple pinned QGIS versions.

Record XML elements, QGIS version, provider, style type, unsupported content, and QGIS reference renders.

### Phase 1 — container and manifest reader

Implement QGS/QGZ loading, QGD discovery, metadata, layer tree, source references, CRS/map views, and diagnostics without rendering.

### Phase 2 — normalized IR and provider contracts

Implement `RenderProject`, `LayerTree`, `DataSourceRef`, `ResourceResolver`, provider capabilities, and compatibility reports.

### Phase 3 — basic vector renderer

Implement a single-symbol renderer, marker/line/fill symbols, categorized and graduated styles, opacity, scale visibility, basic CRS transforms, and PNG output.

### Phase 4 — QML and expression compatibility

Add versioned QML codecs, the declared expression subset, unsupported-feature diagnostics, and cross-version fixture tests.

### Phase 5 — labels and raster

Add basic labels, collision handling, raster compositing, raster classification, and selected data-defined properties.

### Phase 6 — visual compatibility

Run pinned QGIS reference renders and compare dimensions, alpha behavior, layer visibility, feature placement, colors, line widths, labels, and perceptual image metrics.

## Risks and boundaries

- QGS/QGZ is evolving rather than a frozen schema.
- Provider URIs can encode network, database, authentication, or plugin behavior.
- QML contains much more rendering behavior than the initial Rust IR.
- QGIS expressions can reference dynamic scopes and custom functions.
- Font and text rendering can differ by platform.
- Full QGIS visual parity is a long-term compatibility project, not a first implementation milestone.
- QGIS Processing, GUI, plugin, 3D, and print-layout behavior should remain native-QGIS capabilities until separately specified.

## Proposition acceptance criteria

This proposition is ready for implementation planning only when:

- a pinned QGIS fixture corpus exists;
- QGS/QGZ/QML element coverage is inventoried;
- supported providers and styles are selected;
- the normalized IR boundary is reviewed;
- unsupported behavior and diagnostic policy are approved;
- a QGIS reference-render procedure exists;
- pure-Rust, native-QGIS, and WebEngine test gates are separated;
- a feasibility spike demonstrates that at least one real QGS/QGZ vector project can be imported, normalized, rendered, and compared against QGIS with explicit criteria.

No claim of complete QGIS compatibility should be made before those gates pass.
