---
type: Decision
id: D15
title: qgis-sdk CLI is pure Python on typer and questionary
description: "The qgis-sdk command is a pure-Python typer application with questionary prompts for non-web UI scaffolding. The Rust CLI, the PyO3 _core extension and the qgis-plugin name are retired. Supersedes D14."
status: accepted
supersedes: [D14]
tags: [architecture, cli, qgis-sdk, python, typer, questionary]
date: 2026-10-10
---

# D15: qgis-sdk CLI is pure Python on typer and questionary

## Context

D14 chose one Rust implementation of the plugin CLI, reached from Python through a
PyO3 `cli_main` pyfunction in the `qgis_sdk._core` extension. Building that
extension required maturin, a Rust toolchain and a second parser for
`qgis-plugin`. In practice the Rust side was not complete: several commands
(`build`, `test`, `install`, `dev`, `package`, `publish`) printed a message and
returned success without doing their work, and the Python side kept its own
argparse tree and fallbacks. Two implementations existed and neither was the
whole specification.

The SDK is a Python distribution. Its users run it inside QGIS's Python, and
the plugin has no runtime dependency on the SDK. Nothing in the CLI path needs
Rust.

## Decision

### 1. One command, one implementation, in Python

- `qgis-sdk` is the only plugin-development command. It is a console script
  that calls `qgis_sdk.cli:main`, built with **typer**.
- Command behaviour lives in Python modules. There is no native extension, no
  `_core`, no `_fallback_cli`, and no Rust CLI crate.
- `qgis-plugin` is retired. It is not an alias, and no name in the repository
  forwards to it.
- `qgis-cli` stays the GIS-execution CLI in Rust (D13 §1). Plugin tooling does
  not enter it.

### 2. Prompts with questionary, only for non-web scaffolding

`questionary` is used only for non-web scaffolding choices, and only at a terminal
(stdin and stdout are both a TTY). Each question has a flag that answers it for CI:

- `qgis-sdk new` asks for the plugin name (positional argument), `--type`, `--ui/--no-ui`,
  `--author` and `--email`.
- `qgis-sdk ui add-dialog` asks for the dialog name (`--name`).

A non-interactive run never prompts. A missing plugin name then fails with exit code 2.
Web choices (`--web`, `--framework`) stay flags only.

### 3. Every command does what it reports

A command either performs its work or fails with a non-zero exit code. Printing
"Built" or "Created" without writing the artifact is a defect.

- `qgis-sdk package` writes the plugin archive it names.
- *Amended 2026-10-10 (TASK-57):* the `rust` subcommand, every `--rust` flag and the
  cargo passthrough are removed. qgis-sdk contains no Rust, so the plugin CLI does
  not build a crate. A plugin that wants Rust runs cargo itself.
- `metadata_fields()` and `render_metadata_from_dict()` are ported to Python with
  the same field table and output format as the retired Rust functions.

### 4. Build backend

The distribution builds with **setuptools** (`setuptools.build_meta`), with the
bridge assets as explicit package data. Maturin is no longer a build or dev
dependency of `qgis-sdk`. `qgis-py` keeps maturin for its own PyO3 extension.

### 5. Dependencies

`typer` and `questionary` are the qgis-sdk runtime dependencies, declared in
`pyproject.toml` and in the pixi environment. No other dependency is added to
qgis-sdk for the CLI.

## Alternatives considered

- **Keep D14, the native argv forwarder**: rejected. It keeps two
  implementations, a PyO3 build and a Rust toolchain on the CLI path, and it
  leaves the stubbed Rust commands in place.
- **Keep argparse**: rejected. The user chose typer, which gives typed options,
  generated help and one place for prompts.
- **Keep `qgis-plugin` as an alias**: rejected. An alias with a second name is the
  duplicate surface D13 was written to prevent.

## Consequences

- D14 is superseded. Its consequences (the `_core` transport, the loud
  missing-extension error, the completion via `clap_complete`) no longer apply.
  The loud-error rule is kept in spirit: a CLI command never silently succeeds.
- D13 §1 names `qgis-sdk` as the plugin CLI and drops the `qgis-plugin` alias. D13
  §3, §4 and the `CANONICAL_BINARIES`, `FORBIDDEN_EDGES` and `TRACKED_FALLBACKS`
  rules are updated accordingly.
- The `qgis-sdk` wheel is pure Python. It has no compiled artifact and no
  `_core` module.
- The TASK-44 framing ("package the Rust-native CLI and the exact alias") is
  superseded by this record.

## Related records

- [D14 — qgis-sdk CLI transport: native argv forwarding](D14-qgis-sdk-cli-transport-argv-forwarding.md) — superseded by this record.
- [D13 — Rust CLI, FFI, and QGIS SDK product boundaries](D13-rust-cli-ffi-and-qgis-sdk-boundaries.md) — amended by this record.
- [D09 — Wire Protocol over FFI](D09-wire-protocol-over-ffi.md) — unchanged; capability calls between Rust bindings still use it.
