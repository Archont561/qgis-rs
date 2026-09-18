---
type: concept
title: "qgis-rs Public API Design"
description: "Complete public API surface for the qgis-rs ecosystem — Rust library, CLI, HTTP server, and language bindings. Backend-agnostic: works with libqgis_core or pure Rust renderer."
tags: [api, design, rust, rendering, cli, server]
generated: "2026-09-17T14:30:00Z"
status: draft
---

# qgis-rs Public API

The API is organized in four layers:

1. **`qgis-render`** — core Rust library (the engine)
2. **`qgis-cli`** — command-line interface
3. **`qgis-server`** — HTTP server (WMS/WFS/OGC API)
4. **Language bindings** — Python (`qgis-py`), Node.js (`qgis-node`)

---

## 1. Core Library: `qgis-render`

### 1.1 Quick Start

```rust
use qgis_render::prelude::*;

// One-liner: render a QGIS project to PNG
let image = Project::open("map.qgs")?
    .render_to_image(RenderSettings::new(1024, 768))?;

image.save("output.png")?;
```

### 1.2 Project

The `Project` is the central object. It loads a `.qgs`/`.qgz` file and gives you access to layers, styling, CRS, and rendering.

```rust
// Open from file
let project = Project::open("map.qgs")?;
let project = Project::open("map.qgz")?;

// Open from bytes (e.g., uploaded to a server)
let project = Project::from_bytes(&xml_bytes)?;

// Open with options
let project = Project::open_with("map.qgs", OpenOptions::new()
    .trust_layer_metadata(true)       // skip extent/SRS computation
    .skip_invalid_layers(true)        // don't fail on broken layers
    .bad_layer_handler(|uri| {       // handle missing data sources
        eprintln!("bad layer: {}", uri);
        None // or Some(replacement_uri)
    })
)?;

// Project metadata
project.title()                    // → Option<&str>
project.crs()                      // → Crs (the project CRS)
project.extent()                   // → Extent (bounding box of all layers)
project.path()                     // → Option<&Path>
project.layers()                   // → Vec<&Layer>
project.layer("buildings")         // → Option<&Layer> (by name)
project.layer_by_id("abc123")      // → Option<&Layer> (by internal ID)
project.layer_tree()               // → &LayerTree (groups + order)
project.layouts()                  // → Vec<&PrintLayout>
```

### 1.3 Layer

```rust
let layer = project.layer("buildings").unwrap();

// Metadata
layer.name()                       // → &str
layer.id()                         // → &str (internal ID)
layer.layer_type()                 // → LayerType::{Vector, Raster, Mesh, ...}
layer.crs()                        // → Crs
layer.extent()                     // → Extent
layer.feature_count()              // → u64

// Data source
layer.data_source()                // → &DataSource
layer.provider()                   // → &str ("ogr", "postgres", "wms", ...)

// Visibility and styling
layer.is_visible()                 // → bool
layer.set_visible(true)            // toggle
layer.opacity()                    // → f64 (0.0 - 1.0)
layer.set_opacity(0.8)
layer.blend_mode()                 // → BlendMode
layer.renderer()                   // → &Renderer (the symbology)

// Data access (vector layers)
layer.as_vector()                  // → Option<&VectorLayer>
vector_layer.fields()              // → &[Field]
vector_layer.features()            // → FeatureIterator
vector_layer.features_with(request) // → FeatureIterator (with filter)

// Data access (raster layers)
layer.as_raster()                  // → Option<&RasterLayer>
raster_layer.band_count()          // → usize
raster_layer.width()               // → u32
raster_layer.height()              // → u32
raster_layer.read_block(band, extent, width, height) // → RasterBlock
```

### 1.4 Feature Access

```rust
let buildings = project.layer("buildings").unwrap().as_vector().unwrap();

// Iterate all features
for feature in buildings.features() {
    println!("id={} geom={:?}", feature.id(), feature.geometry());
    println!("height={}", feature.get("height").unwrap());
}

// Filtered request — only fetch what you need
let request = FeatureRequest::new()
    .filter(Filter::gt("height", 50))       // WHERE height > 50
    .bounding_box(Extent::new(14.0, 50.0, 15.0, 51.0))
    .select(["name", "height", "geometry"])  // only these columns
    .limit(1000)
    .no_geometry();                          // skip geometry if not needed

for feature in buildings.features_with(request) {
    println!("{}: {}m", feature.get("name")?, feature.get("height")?);
}

// Single feature by ID
let feature = buildings.feature(42)?;

// Spatial query
let request = FeatureRequest::new()
    .intersects(&some_polygon)
    .select_all();

let count = buildings.count_with(request)?;
```

### 1.5 Geometry

```rust
use qgis_render::geometry::*;

// From WKT
let geom = Geometry::from_wkt("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")?;

// From WKB
let geom = Geometry::from_wkb(&bytes)?;

// From GeoJSON
let geom = Geometry::from_geojson(json_value)?;

// Operations
geom.geometry_type()               // → GeometryType::{Point, LineString, Polygon, ...}
geom.is_empty()                    // → bool
geom.is_valid()                    // → bool
geom.area()                        // → f64
geom.length()                      // → f64
geom.centroid()                    // → Option<Point>
geom.bounding_box()                // → Extent
geom.to_wkt()                      // → String
geom.to_wkb()                      // → Vec<u8>
geom.to_geojson()                  // → serde_json::Value
geom.buffer(10.0)                  // → Geometry
geom.intersection(&other)          // → Geometry
geom.union(&other)                 // → Geometry
geom.contains(&point)              // → bool
geom.intersects(&other)            // → bool
geom.distance(&other)              // → f64
geom.simplify(0.01)                // → Geometry (Douglas-Peucker)
geom.transform(&source_crs, &target_crs)?  // → Geometry
```

### 1.6 CRS

```rust
use qgis_render::crs::*;

// Create CRS
let crs = Crs::from_epsg(4326)?;              // WGS 84
let crs = Crs::from_epsg(3857)?;              // Web Mercator
let crs = Crs::from_proj4("+proj=utm +zone=34 +datum=WGS84")?;
let crs = Crs::from_wkt("GEOGCS[\"WGS 84\",...]")?;

// Properties
crs.is_geographic()                // → bool (lat/lon?)
crs.is_projected()                 // → bool
crs.epsg()                         // → Option<u32>
crs.to_wkt()                       // → String
crs.to_proj4()                     // → String

// Transform coordinates
let transform = CoordTransform::new(&Crs::from_epsg(4326)?, &Crs::from_epsg(3857)?)?;
let (x, y) = transform.transform(14.0, 50.0)?;   // lon/lat → meters
let points = transform.transform_batch(&[(14.0, 50.0), (15.0, 51.0)])?;
```

### 1.7 Rendering

```rust
use qgis_render::render::*;

// Basic render to image
let image = project.render_to_image(
    RenderSettings::new(1024, 768)
        .extent(project.extent())               // or custom extent
        .crs(Crs::from_epsg(3857)?)             // output CRS
        .dpi(96)                                // default: 96
        .background(Color::WHITE)               // default: transparent
)?;

image.save("map.png")?;
image.save("map.jpg")?;       // auto-detected from extension
image.to_png_bytes()?;        // → Vec<u8>
image.width()                 // → u32
image.height()                // → u32
image.pixel(x, y)             // → Color

// Advanced: MapSettings gives full control
let settings = MapSettings::new(2048, 2048)
    .extent(Extent::new(14.0, 50.0, 15.0, 51.0))
    .crs(Crs::from_epsg(4326)?)
    .dpi(150)
    .background(Color::rgba(240, 240, 240, 255))
    .layers(&["buildings", "roads", "labels"])   // render only these layers
    .layer_filter("buildings", Filter::gt("height", 10))  // override layer filter
    .antialiasing(true);

let image = project.render(&settings)?;

// Render to different outputs
project.render_to_file(&settings, "map.png")?;
project.render_to_writer(&settings, &mut file)?;
project.render_to_tile(&settings, z, x, y)?;   // single XYZ tile

// Async rendering (for server use)
let image = project.render_async(&settings).await?;
```

### 1.8 Tile Rendering

```rust
use qgis_render::tiles::*;

// Single tile
let tile = project.render_tile(
    TileCoord { z: 12, x: 2190, y: 1362 },
    TileOptions::new(256, 256)         // 256×256 pixel tile
        .crs(Crs::from_epsg(3857)?)    // Web Mercator (default for XYZ)
)?;

tile.png_bytes()               // → Vec<u8>

// Batch render a tile pyramid
let plan = TilePlan::new()
    .zoom_range(10..=14)
    .bounds(Extent::new(14.0, 50.0, 15.0, 51.0))
    .tile_size(256)
    .crs(Crs::from_epsg(3857)?);

// Render to directory ({z}/{x}/{y}.png structure)
plan.render_to_dir(&project, "./tiles/", RenderOptions::new()
    .parallel(8)                        // 8 worker threads
    .progress(|done, total| {
        println!("{done}/{total} tiles rendered");
    })
)?;

// Render to MBTiles
plan.render_to_mbtiles(&project, "output.mbtiles", RenderOptions::new()
    .parallel(8)
    .format(TileFormat::Png)            // or Jpeg, WebP
)?;

// Render to PMTiles
plan.render_to_pmtiles(&project, "output.pmtiles", RenderOptions::new()
    .parallel(8)
    .format(TileFormat::WebP)
)?;
```

### 1.9 Expressions

```rust
use qgis_render::expr::*;

// Parse and evaluate
let expr = Expression::parse("\"height\" > 50 AND \"type\" = 'residential'")?;
let result = expr.evaluate(&feature, &context)?;   // → Value
result.as_bool()               // → true

// Expression types
Expression::parse("length($geometry)")?;
Expression::parse("concat(\"name\", ' (', \"height\", 'm)')")?;
Expression::parse("CASE WHEN \"pop\" > 1000 THEN 'big' ELSE 'small' END")?;
Expression::parse("color_ramp_interpolate('RdYlGn', \"value\", 0, 100)")?;

// Use expressions programmatically
let expr = Expression::gt(
    Expression::field("height"),
    Expression::literal(50),
);

// Compile for repeated evaluation (faster)
let compiled = expr.compile(&layer.fields())?;
for feature in layer.features() {
    if compiled.evaluate_bool(&feature)? {
        // ...
    }
}
```

### 1.10 Print Layouts

```rust
use qgis_render::layout::*;

let layout = project.layout("A4 Landscape")?;

// Render to image
let image = layout.render_to_image(LayoutRenderSettings::new()
    .dpi(300)
)?;
image.save("map_a4.png")?;

// Render to PDF
layout.render_to_pdf("map_a4.pdf", LayoutRenderSettings::new()
    .dpi(300)
)?;

// Render to SVG
layout.render_to_svg("map_a4.svg")?;

// Override extent (e.g., different area than the project default)
let image = layout.render_to_image(LayoutRenderSettings::new()
    .dpi(300)
    .map_extent(Extent::new(14.0, 50.0, 15.0, 51.0))  // override map frame extent
)?;

// List layout items
for item in layout.items() {
    println!("{}: {} at ({}, {})",
        item.id(),
        item.item_type(),   // MapFrame, Legend, ScaleBar, Label, ...
        item.position().x,
        item.position().y,
    );
}
```

### 1.11 Error Handling

```rust
use qgis_render::error::*;

// All fallible operations return Result<T, QgisError>
match Project::open("map.qgs") {
    Ok(project) => { /* ... */ }
    Err(QgisError::FileNotFound(path)) => { /* ... */ }
    Err(QgisError::InvalidProject { message }) => { /* ... */ }
    Err(QgisError::BadLayer { name, uri }) => { /* ... */ }
    Err(QgisError::UnsupportedFormat(fmt)) => { /* ... */ }
    Err(QgisError::RenderError(msg)) => { /* ... */ }
    Err(QgisError::ExpressionError { expr, message }) => { /* ... */ }
    Err(QgisError::CrsError(msg)) => { /* ... */ }
    Err(e) => { /* catch-all */ }
}

// QgisError implements std::error::Error, Display, and From conversions
```

### 1.12 Server Mode (library)

```rust
use qgis_render::server::*;

// Create a server instance from a project
let server = Server::new(Project::open("map.qgs")?)
    .workers(4)                           // 4 render workers
    .tile_cache(CacheConfig::new()
        .memory_mb(512)                   // 512 MB in-memory cache
        .disk_path("./cache/")            // disk fallback
        .ttl(Duration::from_secs(3600))   // 1 hour TTL
    )
    .auth(AuthConfig::new()
        .api_keys(vec!["key-abc123"])
        .anonymous_access(true)           // allow unauthenticated reads
        .rate_limit(100)                  // 100 requests/minute per key
    );

// Handle a WMS request
let response = server.handle_wms(WmsRequest::parse(query_string)?)?;
// response.content_type → "image/png"
// response.body → Vec<u8>

// Handle a WFS request
let response = server.handle_wfs(WfsRequest::parse(query_string)?)?;
// response.content_type → "application/json"

// Handle an OGC API Features request
let response = server.handle_ogcapi(OgcApiRequest {
    path: "/collections/buildings/items",
    query: "limit=10&bbox=14,50,15,51",
})?;
```

---

## 2. CLI: `qgis-cli`

### 2.1 Commands

```
qgis-cli <command> [options]

Commands:
  render    Render a project to an image
  tiles     Render a tile pyramid
  batch     Render multiple extents in parallel
  info      Inspect a project (layers, CRS, extent)
  serve     Start an HTTP tile/map server
  export    Export features from a layer
  mcp       Serve the same capabilities as an MCP server on stdio
  version   Print version information
```

### 2.2 `render`

```bash
# Basic render
qgis-cli render map.qgs -o map.png

# With extent
qgis-cli render map.qgs --extent 14,50,15,51 -o map.png

# With size
qgis-cli render map.qgs --width 2048 --height 1536 -o map.png

# With CRS
qgis-cli render map.qgs --crs EPSG:3857 -o map.png

# Specific layers only
qgis-cli render map.qgs --layers buildings,roads,labels -o map.png

# With DPI (for print quality)
qgis-cli render map.qgs --dpi 300 -o map.png

# Output format (auto-detected from extension, or explicit)
qgis-cli render map.qgs -o map.png      # PNG
qgis-cli render map.qgs -o map.jpg      # JPEG
qgis-cli render map.qgs -o map.webp     # WebP
qgis-cli render map.qgs -o map.svg      # SVG (vector output)
qgis-cli render map.qgs -o map.pdf      # PDF

# Render a specific print layout
qgis-cli render map.qgs --layout "A4 Landscape" -o print.png

# Stdout (for piping)
qgis-cli render map.qgs -o - > map.png
```

### 2.3 `tiles`

```bash
# Basic tile pyramid
qgis-cli tiles map.qgs --zoom 10-14 --bounds 14,50,15,51 -o ./tiles/

# With parallel workers
qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 -o ./tiles/ --parallel 8

# Output to MBTiles
qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 -o output.mbtiles

# Output to PMTiles
qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 -o output.pmtiles

# Tile format and size
qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 -o ./tiles/ \
    --format webp --tile-size 512

# Dry run (count tiles without rendering)
qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 --dry-run
# → Would render 12,847 tiles across zoom levels 10-14
```

### 2.4 `batch`

```bash
# Render multiple extents from a CSV file
# extents.csv: name,minx,miny,maxx,maxy
#              berlin,13.08,52.33,13.76,52.68
#              paris,2.22,48.81,2.47,48.91
qgis-cli batch map.qgs --extents extents.csv -o ./renders/ \
    --size 2048x1536 --parallel 4

# Output naming: ./renders/berlin.png, ./renders/paris.png, ...

# Render all regions at different zoom levels
qgis-cli batch map.qgs --extents regions.geojson -o ./renders/ \
    --size 4096x3072 --parallel 8 --dpi 150
```

### 2.5 `info`

```bash
$ qgis-cli info map.qgs

Project: Berlin Transit Map
CRS:     EPSG:4326 (WGS 84)
Extent:  13.082, 52.338, 13.761, 52.675
Layers:  5

  Name              Type     Provider   CRS       Features
  ────────────────  ───────  ────────   ────────  ────────
  transit_stops     Vector   GeoPackage EPSG:4326   1,247
  rail_lines        Vector   GeoPackage EPSG:4326     89
  buildings         Vector   PostGIS    EPSG:25833  48,392
  terrain           Raster   GeoTIFF    EPSG:4326   —
  labels            Vector   GeoPackage EPSG:4326   3,102

Print Layouts: 2
  A4 Portrait (210×297mm)
  A3 Landscape (420×297mm)
```

### 2.6 `serve`

```bash
# Start HTTP server
qgis-cli serve map.qgs --port 8080

# With options
qgis-cli serve map.qgs --port 8080 \
    --workers 4 \
    --cache 512mb \
    --auth-key my-secret-key

# Multi-project
qgis-cli serve --projects-dir ./maps/ --port 8080

# Endpoints available after starting:
#   GET /wms?SERVICE=WMS&...           → WMS 1.3
#   GET /wfs?SERVICE=WFS&...           → WFS 1.1
#   GET /tiles/{z}/{x}/{y}.png         → XYZ tiles
#   GET /collections                   → OGC API Features
#   GET /collections/{name}/items      → GeoJSON features
#   GET /health                        → health check
#   GET /                              → landing page (JSON)
```

### 2.7 `export`

```bash
# Export features to GeoJSON
qgis-cli export map.qgs --layer buildings -o buildings.geojson

# With filter
qgis-cli export map.qgs --layer buildings \
    --filter "\"height\" > 50" -o tall_buildings.geojson

# With bbox
qgis-cli export map.qgs --layer buildings \
    --bbox 14.0,50.0,15.0,51.0 -o buildings.geojson

# Select columns
qgis-cli export map.qgs --layer buildings \
    --select name,height,geometry -o buildings.geojson

# Output formats
qgis-cli export map.qgs --layer buildings -o buildings.gpkg     # GeoPackage
qgis-cli export map.qgs --layer buildings -o buildings.fgb      # FlatGeobuf
qgis-cli export map.qgs --layer buildings -o buildings.csv      # CSV (WKT geometry)
qgis-cli export map.qgs --layer buildings -o buildings.geojsonl  # GeoJSON Lines
```

### 2.8 `mcp`

```bash
# Serve the Model Context Protocol on stdin/stdout
qgis-cli mcp

# Print the tool catalogue and exit
qgis-cli mcp --list-tools
```

The MCP server is bundled into the `qgis-cli` binary — no separate install, no
Node runtime. It is implemented in `crates/qgis-mcp` on top of
[rmcp](https://github.com/modelcontextprotocol/rust-sdk), the official Rust MCP
SDK, and started inside a Tokio runtime by `qgis-cli`. Building with
`--no-default-features` drops it (and rmcp + Tokio) from the binary.

Tools mirror the subcommands, so a client and a shell script can do the same
things:

| Tool | Mirrors | Arguments |
|------|---------|-----------|
| `capabilities` | — | — |
| `crs_info` | — | `auth_id` |
| `plan_tiles` | `tiles --dry-run` | `bounds`, `zoom` |
| `project_info` | `info` | `project` |
| `render_map` | `render` | `project`, `output`, `extent`, `width`, `height`, `crs`, `dpi`, `layers`, `layout` |
| `export_features` | `export` | `project`, `layer`, `output`, `filter`, `bbox`, `fields` |

Rules the server follows:

* **stdout belongs to the protocol.** Diagnostics go to stderr.
* **Validate before refusing.** `render_map` and `export_features` check the
  project path, output format, extent and CRS, and only then report that the
  operation needs the QGIS backend — so clients can be written against the
  final shape today.
* **Say what is live.** `capabilities` returns the catalogue with a
  `needs_qgis_backend` flag per tool, generated from the router itself so it
  cannot drift from the registered tools.
* **Errors are JSON-RPC errors**, with the `qgis-render` message as the detail.

Client configuration (Claude Desktop):

```json
{ "mcpServers": { "qgis": { "command": "/path/to/qgis-cli", "args": ["mcp"] } } }
```

`crates/qgis-cli/tests/mcp_stdio.rs` spawns the real binary and drives it
through `initialize` → `notifications/initialized` → `tools/list` →
`tools/call`, so the handshake is covered end to end rather than mocked.

---

## 3. HTTP Server: `qgis-server`

### 3.1 Endpoints

```
GET  /                              → Landing page (JSON)
GET  /health                        → Health check

── WMS 1.3 ──────────────────────────────────────────────────
GET  /wms?SERVICE=WMS&REQUEST=GetCapabilities
GET  /wms?SERVICE=WMS&REQUEST=GetMap&LAYERS=buildings&...
GET  /wms?SERVICE=WMS&REQUEST=GetFeatureInfo&...

── WFS 1.1 ──────────────────────────────────────────────────
GET  /wfs?SERVICE=WFS&REQUEST=GetCapabilities
GET  /wfs?SERVICE=WFS&REQUEST=DescribeFeatureType&TYPENAME=buildings
GET  /wfs?SERVICE=WFS&REQUEST=GetFeature&TYPENAME=buildings&...

── XYZ Tiles ────────────────────────────────────────────────
GET  /tiles/{z}/{x}/{y}.png         → Raster tile
GET  /tiles/{z}/{x}/{y}@2x.png      → Retina tile (512px)

── OGC API Features ─────────────────────────────────────────
GET  /collections                   → List collections
GET  /collections/{id}              → Collection metadata
GET  /collections/{id}/items        → Features (GeoJSON)
GET  /collections/{id}/items/{fid}  → Single feature
GET  /collections/{id}/queryables   → Queryable properties

── OGC API Maps ─────────────────────────────────────────────
GET  /map                           → Render full extent
GET  /map?bbox=...&width=...&...    → Render custom extent

── OGC API Tiles ────────────────────────────────────────────
GET  /tiles                         → Tile matrix metadata
GET  /tiles/{tileMatrixSet}/{z}/{y}/{x} → Tile
```

### 3.2 Response Examples

**Landing page:**
```json
{
  "title": "Berlin Transit Map",
  "links": [
    { "href": "/wms?SERVICE=WMS&REQUEST=GetCapabilities", "rel": "service", "type": "application/xml", "title": "WMS 1.3" },
    { "href": "/wfs?SERVICE=WFS&REQUEST=GetCapabilities", "rel": "service", "type": "application/xml", "title": "WFS 1.1" },
    { "href": "/collections", "rel": "data", "type": "application/json", "title": "OGC API Features" },
    { "href": "/tiles/{z}/{x}/{y}.png", "rel": "item", "type": "image/png", "title": "XYZ Tiles" }
  ]
}
```

**GET /collections:**
```json
{
  "collections": [
    {
      "id": "buildings",
      "title": "Buildings",
      "description": "Building footprints for Berlin",
      "extent": {
        "spatial": { "bbox": [[13.08, 52.33, 13.76, 52.68]], "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84" }
      },
      "itemType": "feature",
      "links": [
        { "href": "/collections/buildings/items", "rel": "items", "type": "application/geo+json" },
        { "href": "/collections/buildings/queryables", "rel": "queryables", "type": "application/schema+json" }
      ]
    }
  ]
}
```

**GET /collections/buildings/items?limit=2&bbox=13.3,52.4,13.5,52.6:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": 1,
      "geometry": { "type": "Polygon", "coordinates": [[[13.4, 52.5], [13.41, 52.5], [13.41, 52.51], [13.4, 52.51], [13.4, 52.5]]] },
      "properties": { "name": "Fernsehturm", "height": 368.0, "type": "tower" }
    },
    {
      "type": "Feature",
      "id": 2,
      "geometry": { "type": "Polygon", "coordinates": [[[13.37, 52.52], [13.38, 52.52], [13.38, 52.53], [13.37, 52.53], [13.37, 52.52]]] },
      "properties": { "name": "Reichstag", "height": 47.0, "type": "government" }
    }
  ],
  "links": [
    { "href": "/collections/buildings/items?limit=2&offset=0", "rel": "self" },
    { "href": "/collections/buildings/items?limit=2&offset=2", "rel": "next" }
  ],
  "numberMatched": 48392,
  "numberReturned": 2
}
```

### 3.3 Multi-Project Server

```bash
qgis-cli serve --projects-dir ./maps/

# Routes by project name:
#   /berlin/wms?SERVICE=WMS&...
#   /berlin/wfs?SERVICE=WFS&...
#   /berlin/tiles/{z}/{x}/{y}.png
#   /berlin/collections/buildings/items
#
#   /paris/wms?SERVICE=WMS&...
#   /paris/tiles/{z}/{x}/{y}.png
#
#   /warsaw/wms?SERVICE=WMS&...
```

---

## 4. Python Bindings: `qgis-py`

```python
from qgis_render import Project, RenderSettings, Extent, Crs

# Open project
project = Project.open("map.qgs")
print(project.title)           # "Berlin Transit Map"
print(project.crs)             # Crs("EPSG:4326")
print(project.extent)          # Extent(13.08, 52.33, 13.76, 52.68)
print(project.layers)          # ["transit_stops", "rail_lines", "buildings", ...]

# Render to image
image = project.render(RenderSettings(
    width=1024, height=768,
    extent=project.extent,
    dpi=150,
))
image.save("map.png")

# Access features
buildings = project.layer("buildings")
print(buildings.feature_count)  # 48392

for feature in buildings.features(limit=10):
    print(feature["name"], feature["height"])

# Filtered query
for feature in buildings.features(
    filter='"height" > 100',
    bbox=(13.3, 52.4, 13.5, 52.6),
    select=["name", "height"],
):
    print(feature["name"], feature["height"])

# Tile rendering
from qgis_render import TilePlan

plan = TilePlan(
    zoom=range(10, 15),
    bounds=Extent(13.08, 52.33, 13.76, 52.68),
    tile_size=256,
)
plan.render_to_dir(project, "./tiles/", parallel=8)

# Print layouts
layout = project.layout("A4 Portrait")
layout.render_to_pdf("print.pdf", dpi=300)

# Expressions
from qgis_render import Expression

expr = Expression.parse('"height" > 50 AND "type" = \'residential\'')
result = expr.evaluate(feature)  # True

# Server mode
from qgis_render import Server

server = Server(project, workers=4)
response = server.handle_request("/wms?SERVICE=WMS&REQUEST=GetMap&...")
# response.content_type → "image/png"
# response.body → bytes
```

---

## 5. Node.js Bindings: `qgis-node`

```javascript
const { Project, RenderSettings, Extent } = require("qgis-render");

// Open project
const project = await Project.open("map.qgs");
console.log(project.title);     // "Berlin Transit Map"
console.log(project.layers);    // ["transit_stops", "rail_lines", ...]

// Render to PNG
const image = await project.render(new RenderSettings({
    width: 1024,
    height: 768,
    extent: project.extent,
}));
await image.save("map.png");
// or: const buffer = await image.toPngBuffer();

// Access features
const buildings = project.layer("buildings");
const features = await buildings.features({
    filter: '"height" > 50',
    bbox: [13.3, 52.4, 13.5, 52.6],
    limit: 10,
});
for (const f of features) {
    console.log(f.properties.name, f.properties.height);
}

// Tile rendering
await project.renderTiles({
    zoom: [10, 14],
    bounds: [13.08, 52.33, 13.76, 52.68],
    output: "./tiles/",
    parallel: 8,
    onProgress: (done, total) => {
        console.log(`${done}/${total}`);
    },
});

// Use with Express
const express = require("express");
const app = express();

app.get("/wms", async (req, res) => {
    const response = await server.handleWms(req.query);
    res.type(response.contentType).send(response.body);
});

app.get("/tiles/:z/:x/:y.png", async (req, res) => {
    const { z, x, y } = req.params;
    const tile = await project.renderTile(+z, +x, +y);
    res.type("image/png").send(tile.pngBytes);
});
```

---

## 6. Type Reference

### Core types

```rust
pub struct Project { /* ... */ }
pub struct Layer { /* ... */ }
pub struct VectorLayer { /* ... */ }
pub struct RasterLayer { /* ... */ }
pub struct Feature { /* ... */ }
pub struct Field { /* ... */ }

pub struct Extent {
    pub min_x: f64,
    pub min_y: f64,
    pub max_x: f64,
    pub max_y: f64,
}

pub struct Crs { /* opaque */ }
pub struct CoordTransform { /* opaque */ }

pub struct RenderSettings { /* builder */ }
pub struct MapSettings { /* builder */ }
pub struct Image { /* pixel buffer */ }

pub struct TileCoord { pub z: u8, pub x: u32, pub y: u32 }
pub struct TilePlan { /* builder */ }
pub struct TileOptions { /* builder */ }

pub struct Expression { /* parsed expression */ }
pub struct CompiledExpression { /* optimized for repeated eval */ }

pub struct FeatureRequest { /* builder */ }
pub struct FeatureIterator { /* lazy iterator */ }

pub enum LayerType { Vector, Raster, Mesh, VectorTile, PointCloud, Annotation }
pub enum GeometryType { Point, MultiPoint, LineString, MultiLineString, Polygon, MultiPolygon, GeometryCollection }
pub enum BlendMode { Normal, Multiply, Screen, Overlay, Darken, Lighten, ColorDodge, ColorBurn, HardLight, SoftLight, Difference, Exclusion }
pub enum TileFormat { Png, Jpeg, WebP }

pub struct Color { /* RGBA */ }
impl Color {
    pub const WHITE: Color;
    pub const BLACK: Color;
    pub const TRANSPARENT: Color;
    pub fn rgb(r: u8, g: u8, b: u8) -> Self;
    pub fn rgba(r: u8, g: u8, b: u8, a: u8) -> Self;
    pub fn hex(s: &str) -> Result<Self>;     // "#ff0000" or "ff0000"
}

pub struct DataSource { /* opaque */ }
pub struct PrintLayout { /* ... */ }
pub struct LayoutItem { /* ... */ }
```

### Server types

```rust
pub struct Server { /* ... */ }
pub struct ServerConfig { /* builder */ }
pub struct CacheConfig { /* builder */ }
pub struct AuthConfig { /* builder */ }

pub struct WmsRequest { /* parsed WMS params */ }
pub struct WfsRequest { /* parsed WFS params */ }
pub struct OgcApiRequest { pub path: String, pub query: String }

pub struct HttpResponse {
    pub status: u16,
    pub content_type: String,
    pub headers: Vec<(String, String)>,
    pub body: Vec<u8>,
}
```

---

## 7. Design Principles

1. **One-liner for simple cases**: `Project::open("map.qgs")?.render_to_image(RenderSettings::new(1024, 768))?.save("out.png")?;`
2. **Builder pattern for complexity**: `RenderSettings::new(1024, 768).extent(...).crs(...).dpi(...).layers(...)`
3. **Sensible defaults**: 96 DPI, project CRS, project extent, transparent background, all visible layers
4. **Lazy iteration**: `features()` returns an iterator, not a Vec. Memory-efficient for large datasets.
5. **Consistent naming**: `open()`, `render()`, `save()`, `to_*()`, `from_*()` across all types.
6. **Backend-agnostic**: The public API never exposes QGIS C++ types or FFI details. Swap the backend without changing user code.
7. **Result everywhere**: All fallible operations return `Result<T, QgisError>`. No panics in library code.
8. **Sync + async**: Core API is synchronous (simple). Async variants available for server use (`render_async`).
