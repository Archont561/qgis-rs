---
type: Tool
title: Scaffold Task
description: The pixi run scaffold code-generation task for adding new QGIS type bindings.
status: stable
tags: [scaffold, codegen, pixi, task]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# Scaffold Task

## Usage

```bash
pixi run scaffold <layer> <concept> <qgis_class> <short_name>
```

### Arguments

| Argument      | Example     | Description                              |
|---------------|-------------|------------------------------------------|
| `layer`       | `core`      | QGIS library layer (core, gui, analysis) |
| `concept`     | `geometry`  | Directory name for the concept           |
| `qgis_class`  | `QgsGeometry` | Full QGIS C++ class name              |
| `short_name`  | `geometry`  | Short name for files and functions       |

### Example

```bash
pixi run scaffold core geometry QgsGeometry geometry
```

## Generated Files

| File                                           | Purpose                          |
|------------------------------------------------|----------------------------------|
| `include/<layer>/<concept>.h`                  | CXX header with handle + function declarations |
| `src/<layer>/<concept>/<short>.rs`             | `#[cxx::bridge]` with FFI signatures |
| `src/<layer>/<concept>/<short>.cpp`            | C++ shim skeleton with TODO comments |
| `src/<layer>/<concept>/mod.rs`                 | Rust module declaration          |

## Wiring

The scaffold task also:

1. Appends `pub mod <concept>;` to `src/<layer>/mod.rs` (if not already present)
2. Appends a `pub use` alias to `src/lib.rs` (if not already present)

## Post-Scaffold Steps

After scaffolding, you need to:

1. **Edit the header** — add function declarations for your QGIS type's methods
2. **Edit the `.rs` bridge** — add matching Rust signatures
3. **Edit the `.cpp` shim** — implement the functions using real QGIS API
4. **Build** — `pixi run -- cargo build -p qgis-sys`
5. **Test** — add integration tests in `tests/` following [D11](decisions/D11-tests-outside-src.md)

The scaffold/API documentation work is tracked by [TASK-3](../backlog/tasks/task-3%20-%20Document%20and%20scaffold%20the%20declarative%20plugin%20and%20SDK%20APIs.md); concrete bindings are tracked by [TASK-5](../backlog/tasks/task-5%20-%20Bind-QgsFields-and-QgsField-schema-types-in-qgis-sys.md) through [TASK-7](../backlog/tasks/task-7%20-%20Bind-QgsFeatureIterator-and-QgsCoordinateReferenceSystem-in-qgis-sys.md).

## Template Details

The generated header includes:
- Handle declaration via `QGIS_DECLARE_HANDLE`
- Include of the generated `.rs.h` bridge header
- Placeholder function signatures

The generated C++ shim includes:
- `QGIS_DEFINE_HANDLE_DTOR` (commented out)
- `QGIS_HANDLE_CAST` (commented out)
- TODO comments for function implementations
