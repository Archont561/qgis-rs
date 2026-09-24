---
type: Practice
title: Environment Provisioning
description: How qgis-rs bootstraps its development environment via pixi-sandbox transports when pixi/conda are unavailable.
status: stable
tags: [environment, pixi-sandbox, provisioning, sandbox, offline]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
sources:
  - id: pixi-sandbox
    resource: https://github.com/Archont561/pixi-sandbox
    title: "pixi-sandbox — Portable, verifiable Pixi environments for sandboxed machines"
    author: human:archont561
  - id: publish-automation
    resource: https://github.com/Archont561/pixi-sandbox/blob/main/.knowledge/publish-automation.md
    title: "pixi-sandbox — Release-driven sandbox publication"
    author: human:archont561

---

# Environment Provisioning

## The Problem

qgis-rs requires a complex conda-forge environment: QGIS ≥3.44, Rust ≥1.96, clang-tools ≥22, cxx-compiler, lefthook, and convco. Normally this is solved by `pixi install` — but in sandboxed machines, **conda-forge, prefix.dev, and static.rust-lang.org are all unreachable**.

The only reliable network path is `github.com` over the git protocol. This is the same constraint class that [pixi-sandbox](https://github.com/Archont561/pixi-sandbox) was designed to solve.

## The Solution: pixi-sandbox

[pixi-sandbox](https://github.com/Archont561/pixi-sandbox) packages entire conda environments as a git transport (raw `.conda` files, helper tools, optional cargo vendor), distributes it via orphan git branches, and restores it offline. The consumer needs only `sh`, `git`, and `sha256sum`.

qgis-rs is a **consumer** of pixi-sandbox (release mode): it does not vendor the pixi-sandbox crate. The reviewed publish plan lives in `.pixi-sandbox.toml` at the repo root.

### Producer (CI)

The `.github/workflows/publish_sandbox.yml` workflow is a thin wrapper around the *reusable* pixi-sandbox publisher (`Archont561/pixi-sandbox/.github/workflows/publish-sandbox.yml`, pinned to an immutable commit SHA). On `workflow_run` after a successful `CI` run on `main` (or on `workflow_dispatch`), it:

1. Validates `.pixi-sandbox.toml` via `pixi-sandbox plan --json`.
2. Expands the plan into one native job per (bundle × platform) — here the single `developer` bundle (environments `dev` + `docs`, platform `linux-64`).
3. On each native runner: `pixi install --frozen -e <env>` → `pack --self-bin <verified release> --cargo-vendor` → `doctor --verify` → `publish` (one orphan branch, force-pushed).
4. The same checksum-verified standalone release binary is embedded as the branch bootstrap executable.

The branch published is `sandbox/developer-linux-64`. Packing, verifying and publishing all run on the *same* native runner — the payload never travels as an artifact.

`pixi-pack` / `pixi-unpack` are **not** local dependencies: the release binary fetches them from its own embedded SHA-256 pins (`--fetch-tools`), so the checked-in `pixi.lock` does not need to carry pack tooling.

### Consumer (sandbox / local)

```sh
# From any machine with git + bash (no pixi, no conda):
bash scripts/restore.sh
# default branch: sandbox/developer-linux-64
# default output: .
```

`scripts/restore.sh` fetches the branch (via a worktree), runs `doctor --verify` on the transport, and calls the branch's own `restore.sh` / embedded binary to materialise the environments and vendor tree into the current repo, then sources `.pixi/sandbox-env.sh` and puts `dev` env + bundled tools on PATH — so `build.rs` finds Qt and QGIS headers, and `cargo build --offline` works.

## Network Reachability Matrix

| Endpoint                    | Reachable? | Used by                  |
|-----------------------------|-----------|--------------------------|
| `github.com` (git)          | ✔        | Clone/fetch sandbox branch |
| `conda.anaconda.org`        | ✘        | `pixi install`           |
| `prefix.dev`                | ✘        | pixi-build backends      |
| `static.rust-lang.org`      | ✘        | `rustup install`         |
| `static.crates.io`          | ✘        | `cargo build` (online)   |
| `registry.npmjs.org`        | ✔        | npm (not needed here)    |

## Scripts

| Script                  | Purpose                                              |
|-------------------------|------------------------------------------------------|
| `scripts/restore.sh`    | Fetch the published sandbox branch and restore dev/docs offline |

## What the Transport Contains

Based on `pixi.toml`:

| Package        | Purpose                                |
|----------------|----------------------------------------|
| `rust` ≥1.96   | cargo, rustc, rustfmt, clippy-driver  |
| `cxx-compiler` | C++ compiler for cxx-build + cc        |
| `clang-tools` ≥22 | clang-format, clang-tidy           |
| `lefthook` ≥2.1 | Git hooks manager                     |
| `convco` ≥0.6   | Conventional commit checker           |
| `qgis` ≥3.44   | QGIS headers, libraries, plugins       |
| `pixi`         | Environment manager (for `pixi run` tasks) |

Blobs are verified against the manifest's SHA-256 digests before anything is written. The vendor tree (when `cargo_vendor = true`, as here) is always materialised so `cargo build --offline` works regardless of which environments were selected.

## Using Tools After Restore

```sh
bash scripts/restore.sh
cargo build -p qgis-sys          # works — cargo on PATH (offline)
clang-format --version            # works — clang-tools on PATH
pixi --version                   # works — bundled pixi
QT_QPA_PLATFORM=offscreen cargo test -p qgis-sys --test application_info -- --test-threads=1
```

## Relationship to pixi.toml

The `pixi.toml` remains the single source of truth for environment definition. The sandbox transport is a **pre-computed snapshot** of that definition — produced in CI by the reusable publisher, consumed where pixi can't install.

When `pixi.toml` or `pixi.lock` changes, CI runs and the `publish-sandbox` workflow republishes the bundle. The environments actually published are gated by `.pixi-sandbox.toml` (explicit, reviewed bundles — never "every environment"), not by the manifest alone.