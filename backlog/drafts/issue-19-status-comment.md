Tracking this RFC in the backlog, and recording where the repository already stands against it.

Related backlog task: [TASK-25.4 — resolve RFC 19 open questions and record the native-manager ADR](https://github.com/Archont561/qgis-rs/blob/566b579/backlog/tasks/task-25.4%20-%20RFC-19-resolve-open-questions-and-record-the-native-manager-ADR.md).

**Phase 1 is shipped.** PR #20 landed the protocol crate, the router, the envelope and the single-function bindings: thirteen operations, one `invoke` on each of the Python and Node edges, golden values asserted identically from Rust, Python and TypeScript. So the first bullet of the migration sketch is done, with one difference from the text above — the RFC writes `transportVersion`, but the shipped wire is **snake_case throughout**, including operation names (`engine_info`, `tile_from_lon_lat`, …), with JavaScript renaming at its own edge. Three clients and their golden tests agree on that today, so the RFC should either be read with snake_case substituted or amended.

**Phases 2 to 4 are now tracked as backlog tasks:**

| Task | Scope |
| --- | --- |
| `TASK-25` | This RFC: open questions, the ADR that settles them, closing condition (no `cxx`/`cxx-build` left in `qgis-sys`) |
| `TASK-25.1` | Phase 2 — manager TU, ID registry, `-fvisibility=hidden`, catch-all fence, `app.init`/`engine.info` plus the existing vector-layer shims |
| `TASK-25.2` | Phase 3 — `layer.open`/`info`/`close` and a batched `layer.features` (D06) |
| `TASK-25.3` | Phase 4 — `render_map`/`export_features` live, `NEEDS_QGIS` deleted, dynamic `capabilities` |

**One prerequisite the RFC does not mention:** the repository has no C++ build system. Every `.cpp` is compiled by `build.rs` through `cc`/`cxx-build` straight into the Rust link line. That cannot express a shared library with `-fvisibility=hidden` and exactly three default-visible symbols, and it cannot build the GoogleTest binary `TASK-23` asks for. `cmake` and `ninja` are not in `pixi.lock` either. `TASK-24` covers adding them; note that the lock cannot be re-solved from the dev sandbox (conda-forge is unreachable there), so that solve and a sandbox-pack republish have to happen on a runner.

**Feasibility note:** the gated suite (`tests/application_lifecycle.rs`, `tests/vector_layer.rs`) runs a real `QgsApplication` and a real vector layer headless and passes, so phase 2 has a working acceptance surface today. The concurrency question — one global mutex versus a dedicated QGIS thread — is the thing that blocks starting it, because it decides the shape of the manager rather than being an implementation detail inside it.

---

## Architecture resolution ready to post

The open questions are resolved in `.knowledge/decisions/D12-qgis-native-manager-over-c-abi.md`:

- Use one dedicated QGIS owner/executor thread with a blocking request queue; a mutex alone is insufficient because it does not preserve QGIS/Qt thread affinity across callers.
- Keep `crates/qgis-protocol` as the normative source for the transport version, closed operation set, envelope, error kinds, and `snake_case` wire names. A versioned JSON Schema artifact will be emitted from that crate for C++ conformance tests.
- Keep rendered images and exported feature files path-based, returning metadata rather than base64 or arbitrary binary payloads.
- Keep crash isolation out of RFC 19 v1. The C++ exception fence and structured errors are required, but segfaults, aborts, memory corruption, and plugin crashes require a later subprocess/stdin transport.
- Amend the RFC's illustrative camelCase keys (`transportVersion`, `layerId`, `isValid`, `featureCount`) to the shipped `snake_case` keys (`transport_version`, `layer_id`, `is_valid`, `feature_count`). Future RFC 19 operations use `layer_open`, `layer_info`, `layer_close`, and `layer_features`.

The issue comment could not be posted by the configured GitHub integration: GitHub returned `Resource not accessible by integration` for the write request. The text above is retained here until the issue can be updated.
