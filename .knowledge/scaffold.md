---
type: Tool
title: Native-manager Operation Scaffold
description: Add a reviewed operation to the qgis-sys native-manager API manifest.
status: stable
tags: [scaffold, codegen, pixi, native-manager]
---

# Native-manager Operation Scaffold

RFC 19 and [D12](decisions/D12-qgis-native-manager-over-c-abi.md) replaced the
per-concept CXX bridge layout. The scaffold command no longer creates headers,
`#[cxx::bridge]` modules, C++ shims, or `src/<layer>/<concept>/` trees.

## Usage

```bash
pixi run scaffold <operation> <handler>
# equivalently:
pixi run xtask scaffold <operation> <handler>
```

Both arguments are identifiers from the native-manager contract:

- `operation` is the snake_case protocol operation, such as `project_save`.
- `handler` is the C++ handler identifier registered for that operation.

The command adds a `supported_manual` declaration and operation to
`crates/qgis-sys/native_manager/generated/api_manifest.json`, validates the
whole manifest, and regenerates:

- `include/native_manager/generated/api_manifest.h`
- `include/native_manager/generated/operation_table.inc`

It refuses to overwrite an existing operation. The generated declaration is a
review prompt, not a completed binding: review its version and semantics,
implement the handler in the native manager, and add an integration test under
`crates/qgis-sys/tests/`. Run `pixi run xtask api-manifest --check` to verify
that the checked-in fragments still match the JSON source of truth.
