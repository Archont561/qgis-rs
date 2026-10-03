# Decisions

Architectural decision records for qgis-rs. Each document captures a decision, its rationale, alternatives considered, and consequences.

## Active Decisions

* [D12 — QGIS Native Manager over the C ABI](/decisions/D12-qgis-native-manager-over-c-abi.md) - QGIS state has one dedicated owner thread, `qgis-protocol` is normative, artifacts stay path-based, and crash isolation is deferred.
* [D11 — Tests Outside `src/`](/decisions/D11-tests-outside-src.md) - One layout in every language: source in `src/`, tests in `tests/`, and anything a test needs is public.
* [D10 — xtask over Shell Scripts](/decisions/D10-xtask-over-shell-scripts.md) - Repository automation is a compiled, tested `cargo xtask` binary behind pixi tasks; per-package verbs stay with turbo.
* [D09 — Wire Protocol over FFI](/decisions/D09-wire-protocol-over-ffi.md) - Each binding exposes one `invoke(json) -> json`; the versioned protocol is the interface, not a mirrored class surface.
* [D08 — Standalone Rendering App](/decisions/D08-standalone-rendering-app.md) - Embed QGIS as a headless rendering engine in a Rust application (recommended path).
* [D07 — Rust QGIS Plugins via PyO3](/decisions/D07-rust-qgis-plugins.md) - Use Rust as the computation engine behind QGIS Processing plugins.

## Foundational Decisions

* [D01 — Two-Crate Architecture](/decisions/D01-two-crate-architecture.md) - Split into qgis-sys (raw FFI) and qgis (safe wrappers).
* [D02 — Ownership Model](/decisions/D02-ownership-model.md) - Transfer semantics for Qt parent-child vs Rust ownership.
* [D03 — Error Handling](/decisions/D03-error-handling.md) - Structured Results with QgsError side-channel.
* [D04 — API Binding Priority](/decisions/D04-api-priority.md) - Tiered approach: bind the 20% that covers 80% of workflows.
* [D05 — Threading Model](/decisions/D05-threading.md) - Accept single-threaded, all QGIS types are `!Send + !Sync`.
* [D06 — String Strategy](/decisions/D06-string-strategy.md) - Convert at the boundary, cache metadata, batch-extract for hot paths.
