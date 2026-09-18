# Project Context

This document provides essential context for developers and AI agents working on qgis-rs.

## What is qgis-rs?

**qgis-rs** is a Rust library that provides safe, idiomatic bindings to the QGIS C++ API. It enables Rust developers to:

- Render QGIS projects (`.qgs`/`.qgz` files) to images
- Access and manipulate geospatial data (vectors, rasters)
- Build high-performance GIS servers and CLI tools
- Create QGIS plugins with Rust acceleration

## Why Does This Exist?

### The Problem

QGIS is the world's most popular open-source GIS platform, but it's written in C++ with Python bindings (PyQGIS). Developers who want to:

- Build high-performance GIS servers
- Process millions of features in batch
- Deploy GIS functionality without Python/JVM dependencies
- Integrate GIS into Rust applications

...have no good options. PyQGIS is slow, GeoServer requires Java, and QGIS Server is complex to deploy.

### The Solution

qgis-rs provides **safe Rust bindings** to QGIS's C++ core library, enabling:

- **Native performance** — No Python overhead, no JVM
- **Type safety** — Catch errors at compile time
- **Easy deployment** — Single binary, no runtime dependencies
- **Full QGIS power** — Access all QGIS features from Rust

## Technical Architecture

### Layer Model

```
┌─────────────────────────────────────┐
│  Your Application                   │
│  (uses qgis-render API)             │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  qgis-render                        │
│  High-level Rust API                │
│  - Project, Layer, Feature          │
│  - RenderSettings, TilePlan         │
│  - Safe, idiomatic Rust             │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  qgis-sys                           │
│  Low-level CXX bindings             │
│  - FFI declarations                 │
│  - Handle management                │
│  - Type conversions                 │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  QGIS C++ API (libqgis_core.so)     │
│  - QgsProject, QgsVectorLayer       │
│  - QgsMapSettings, QgsGeometry      │
│  - Qt framework                     │
└─────────────────────────────────────┘
```

### Key Design Decisions

1. **CXX over bindgen** — Type-safe FFI with automatic string conversion
2. **Opaque handles** — Hide C++ implementation details from Rust
3. **!Send + !Sync** — Enforce QGIS's single-threaded requirements at compile time
4. **Builder pattern** — Fluent API for configuration objects
5. **Lazy iteration** — Fetch features on-demand, not all at once

### Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **Language** | Rust 1.96+ | Memory safety, performance, modern tooling |
| **FFI** | CXX | Type-safe, automatic conversions, no unsafe boilerplate |
| **Build** | Cargo + cxx-build | Standard Rust tooling with C++ compilation |
| **Dependencies** | Pixi (conda-forge) | Reproducible environments, QGIS packages |
| **Testing** | cargo test + pytest | Standard Rust testing + Python integration tests |
| **Docs** | Astro Starlight | Modern documentation with MDX support |
| **CI** | GitHub Actions | Free for open source, good Rust support |

## Project Structure

```
qgis-rs/
├── crates/
│   ├── qgis-sys/              # Low-level CXX bindings
│   │   ├── src/               # Rust bridge code
│   │   ├── include/           # C++ headers
│   │   └── build.rs           # Build script (cxx-build)
│   ├── qgis-render/           # Rendering engine: projects, extents, CRS, tiles
│   ├── qgis-server/           # HTTP server: WMS, WFS, XYZ tiles, OGC API
│   ├── qgis-mcp/              # Model Context Protocol server (rmcp)
│   ├── qgis-cli/              # Command-line binary, bundles the MCP server
│   ├── qgis-py/               # Rust core of the qgis-rs Python wheel (PyO3 + qgis-cli bin)
│   ├── qgis-sdk/              # Rust core of the qgis-sdk Python wheel (PyO3 + CLIs)
│   └── qgis-node/             # Rust core of the qgis-rs npm package (NAPI + CLIs)
│
├── py-packages/
│   ├── qgis-rs/               # Python dist: pyproject.toml (maturin), python/qgis_rs/, tests/
│   └── qgis-sdk/              # Python dist: pyproject.toml, src/qgis_sdk/, tests/, pixi [package]
│
├── ts-packages/
│   ├── qgis-node/             # npm dist: package.json, index.js, fallback.js, bin/ wrappers
│   └── qgis-sdk-bridge/       # @qgis-sdk/bridge — Bun workspace, TypeScript sources + bun:test
│
├── apps/
│   └── docs/                  # Documentation site (Astro Starlight)
│
├── .knowledge/                # Design documents and decision records
│   ├── INDEX.md              # Entry point
│   ├── architecture.md       # System architecture
│   ├── ROADMAP.md            # Development roadmap
│   ├── decisions/            # Architecture Decision Records
│   └── api-design.md         # Public API specification
│
├── scripts/                   # Bootstrap and utility scripts
├── .github/workflows/         # CI/CD pipelines
│
├── pixi.toml                  # Pixi environment configuration
├── Cargo.toml                 # Rust workspace configuration
└── README.md                  # This file
```

## Development Workflow

### Setup

```bash
# Clone repository
git clone https://github.com/Archont561/qgis-rs.git
cd qgis-rs

# Install dependencies (Pixi)
pixi install

# Activate environment
pixi shell

# Build
cargo build

# Test
cargo test
```

### Common Tasks

```bash
# Format code
pixi run fmt

# Lint code
pixi run lint

# Run tests
pixi run test

# Run full tests (with QGIS environment)
pixi run test-full

# Build documentation
pixi run docs-build

# Start docs dev server
pixi run docs-dev
```

### Adding a New QGIS Class

1. **Research** the QGIS C++ API for the class
2. **Create decision record** in `.knowledge/decisions/` if needed
3. **Add C++ header** in `crates/qgis-sys/include/{layer}/{concept}.h`
4. **Add Rust bridge** in `crates/qgis-sys/src/{layer}/{concept}/{short}.rs`
5. **Add C++ shim** in `crates/qgis-sys/src/{layer}/{concept}/{short}.cpp`
6. **Write tests** in `tests/{concept}.rs`
7. **Update documentation** in `.knowledge/` and `apps/docs/`

Use the scaffold task to generate boilerplate:

```bash
pixi run scaffold core geometry QgsGeometry geometry
```

## Current State (September 2026)

### What Works

- ✅ CXX bindings foundation
- ✅ QgsApplication lifecycle management
- ✅ QgsVectorLayer basics (creation, validity, metadata)
- ✅ Build system (Cargo + cxx-build)
- ✅ CI/CD pipeline (GitHub Actions)
- ✅ Knowledge base (OKF v0.2 compliant)
- ✅ Documentation site (Astro Starlight)

### What's Planned

- 🔨 Rendering pipeline (QgsMapSettings, QgsMapRendererJob)
- 🔨 Geometry operations (QgsGeometry)
- 📋 High-level `qgis-render` API
- 📋 CLI tool (`qgis-cli`)
- 📋 HTTP server (`qgis-server`)
- 📋 Plugin SDK (`qgis-sdk`)

### Known Limitations

- **Thread safety** — QGIS is single-threaded; Rust wrappers enforce this
- **Qt dependency** — Requires Qt 6.x runtime (bundled with QGIS)
- **Platform support** — Linux x86_64 primary, macOS/Windows experimental
- **QGIS version** — Targets QGIS 3.44.9 LTS only

## Key Contacts

- **Maintainer**: [Your Name](mailto:your-email@example.com)
- **GitHub**: https://github.com/Archont561/qgis-rs
- **Issues**: https://github.com/Archont561/qgis-rs/issues
- **Discussions**: https://github.com/Archont561/qgis-rs/discussions

## Resources

### QGIS

- [QGIS C++ API Documentation](https://qgis.org/api/)
- [PyQGIS Developer Cookbook](https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/)
- [QGIS Source Code](https://github.com/qgis/QGIS)

### Rust + C++

- [CXX — Safe FFI between Rust and C++](https://cxx.rs/)
- [The Rust FFI Omnibus](http://jakegoulding.com/rust-ffi-omnibus/)
- [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)

### Geospatial

- [GDAL/OGR](https://gdal.org/) — Geospatial Data Abstraction Library
- [PROJ](https://proj.org/) — Cartographic Projections and Coordinate Transformations
- [GEOS](https://libgeos.org/) — Geometry Engine Open Source

## FAQ

### Why not use PyQGIS?

PyQGIS is great for scripting and plugin development, but it has limitations:

- **Performance** — Python is 10-100× slower than Rust for CPU-bound tasks
- **Deployment** — Requires Python environment with all dependencies
- **Type safety** — Runtime errors instead of compile-time errors
- **Concurrency** — GIL limits parallelism

qgis-rs is for when you need native performance, easy deployment, and type safety.

### Why not use GeoServer?

GeoServer is excellent for serving OGC standards (WMS/WFS), but:

- **Java dependency** — Requires JVM, complex deployment
- **SLD styling** — Can't use QGIS styles directly (lossy conversion)
- **Performance** — Java GC pauses, higher memory usage
- **QGIS features** — Limited to what GeoServer implements

qgis-rs gives you QGIS's full rendering power in a single binary.

### Is this production-ready?

**Not yet.** The project is in active development (v0.1). The API is stabilizing, and we're building out functionality. Expect breaking changes before v1.0.

For production use today, consider:
- **PyQGIS** — Mature, full-featured, large community
- **QGIS Server** — Official QGIS server (C++ with FastCGI)
- **GeoServer** — Java-based OGC server

### Can I contribute?

Yes! See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) for guidelines.

### Where can I get help?

- **GitHub Discussions** — Ask questions, share ideas
- **GitHub Issues** — Report bugs, request features
- **QGIS Mailing Lists** — QGIS-specific questions
- **Rust Users Forum** — Rust-specific questions

## License

Dual-licensed under Apache-2.0 and MIT. See [README.md](README.md#license) for details.

---

**Last Updated**: September 17, 2026
