---
okf_version: "0.2"
---

# qgis-rs — Knowledge Index

# Overview

* [Project Context](/CONTEXT.md) — Orientation file for AI agents and contributors working on qgis-rs.
* [Roadmap](/ROADMAP.md) — Ordered plan: architectural decisions first, then incremental type binding.
* [Update Log](/log.md) — Chronological history of bundle changes.
* [QGIS Plugin SDK](/qgis-plugin-sdk.md) — Python framework for building QGIS plugins with declarative APIs, Rust acceleration, and CLI tooling.
* [QGIS Plugin UI](/qgis-plugin-ui.md) — Dialogs via PyQt/Qt Designer (.ui) and WebEngine with HTML/CSS/JS + QWebChannel bridge (new).

# Architecture

* [Architecture](/architecture.md) — Crate layout, layer model, and FFI data flow for qgis-rs.
* [FFI Shim Pattern](/ffishim.md) — The opaque-handle CXX bridge pattern used to wrap every QGIS C++ type.
* [Build System](/build-system.md) — How build.rs orchestrates cxx-build, cc shim compilation, and compile_commands.json.

# QGIS Concepts

* [QGIS Application Lifecycle](/qgis-application.md) — QgsApplication initialization, the QApplication workaround, and RAII patterns.
* [QGIS Vector Layer](/qgis-vector-layer.md) — QgsVectorLayer binding — creation, validity, metadata accessors.

# Environment and Tooling

* [Environment Provisioning](/env-provisioning.md) — How qgis-rs bootstraps its development environment via pixi-sandbox packs when pixi/conda are unavailable.
* [Pixi](/pixi.md) — Pixi environment manager — conda-forge dependencies, tasks, and features.
* [Lefthook](/lefthook.md) — Pre-commit and commit-msg hooks for formatting, linting, and conventional commits.
* [Scaffold Task](/scaffold.md) — The pixi run scaffold code-generation task for adding new QGIS type bindings.
* [Testing](/testing.md) — Test structure, fixtures, environment variables, and QT_QPA_PLATFORM requirements.
* [Documentation Site](/documentation-site.md) — Astro Starlight documentation site in apps/docs/ with Bun runtime.

# Strategy and Decisions

* [Decisions](/decisions/) — Architectural decision records (D01–D08).

# References

* [Related Approaches](/related-approaches.md) — Comparison of Rust ↔ C++ / Qt binding strategies and how qgis-rs relates to them.
