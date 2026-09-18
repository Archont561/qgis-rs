---
type: Practice
title: Environment Provisioning
description: How qgis-rs bootstraps its development environment via pixi-sandbox packs when pixi/conda are unavailable.
status: stable
tags: [environment, pixi-sandbox, provisioning, sandbox, offline]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
sources:
  - id: pixi-sandbox
    resource: https://github.com/Archont561/pixi-sandbox
    title: "pixi-sandbox — Portable, verifiable Pixi environments for sandboxed machines"
    author: human:archont561
  - id: pixi-sh
    resource: https://pixi.sh
    title: "Pixi — cross-platform, multi-language package manager"
    author: team:prefix-dev

---

# Environment Provisioning

## The Problem

qgis-rs requires a complex conda-forge environment: QGIS ≥3.44, Rust ≥1.96, clang-tools ≥22, cxx-compiler, lefthook, and convco. Normally this is solved by `pixi install` — but in sandboxed machines, **conda-forge, prefix.dev, and static.rust-lang.org are all unreachable**.

The only reliable network path is `github.com` over the git protocol. This is the same constraint class that [pixi-sandbox](https://github.com/Archont561/pixi-sandbox) was designed to solve.

## The Solution: pixi-sandbox

[pixi-sandbox](https://github.com/Archont561/pixi-sandbox) packages entire conda environments as self-extracting `.sh` bundles, distributed via orphan git branches. The consumer needs only `sh`, `git`, `tar`, and `sha256sum` — all available in virtually every Unix sandbox.

### Producer (CI)

The `.github/workflows/env.yml` workflow:

1. Installs pixi on a hosted runner (full network access)
2. Resolves `pixi install -e default` (deliberately not `--locked`, as in the
   reference project, so a manifest change never reddens this job by itself)
3. Runs `pixi run -e default pack`, i.e. `scripts/pack-env.sh`: `pixi-pack
   --create-executable` produces `dist/qgis-rs-<platform>.sh`, then the script
   unpacks it into a scratch dir with the extractor's own flags
   (`-o <dir> -e env`) and prints `pixi`/`cargo`/`rustc`/`bun --version` from
   the unpacked environment
4. Force-pushes `dist/` to the orphan branch `env/qgis-rs-linux-64`

`pixi-pack` is a declared dependency (`[workspace.dependencies]`, consumed by
the root environment) rather than something the workflow installs ad hoc, which
is what makes `pixi run -e default pack` find the tool. After adding or bumping
a pin, run `pixi lock` and commit the result so the checked-in `pixi.lock`
matches `pixi.toml`.

### Consumer (sandbox / local)

```sh
# Option A: full script
sh scripts/setup-env.sh

# Option B: manual
git clone --depth 1 --branch env/qgis-rs-linux-64 \
  https://github.com/Archont561/qgis-rs pack
cd pack && bash ./pixi-sandbox-*.sh
```

Then activate:

```sh
. scripts/use-pack.sh
# or: PIXI_SANDBOX_HOME=.pixi-sandbox . scripts/use-pack.sh
```

This puts `env/bin` on PATH and sets `CONDA_PREFIX`, so `build.rs` finds Qt and QGIS headers automatically.

## Network Reachability Matrix

| Endpoint                    | Reachable? | Used by                  |
|-----------------------------|-----------|--------------------------|
| `github.com` (git)          | ✔        | Clone env branch         |
| `conda.anaconda.org`        | ✘        | `pixi install`           |
| `prefix.dev`                | ✘        | pixi-build backends      |
| `static.rust-lang.org`      | ✘        | `rustup install`         |
| `static.crates.io`          | ✘        | `cargo build` (online)   |
| `registry.npmjs.org`        | ✔        | npm (not needed here)    |

## Scripts

| Script                          | Purpose                                              |
|---------------------------------|------------------------------------------------------|
| `scripts/setup-env.sh`          | Clone env branch + run self-extractor + write receipt |
| `scripts/use-pack.sh`           | Source to put pack tools on PATH + set CONDA_PREFIX  |
| `scripts/publish-env-branch.sh` | CI helper: force-push dist/ to orphan env/ branch    |

## Receipt

After `setup-env.sh` completes, `.pixi-sandbox/env-pack-receipt.json` records:

```json
{
  "protocol": 1,
  "pack": "qgis-rs",
  "platform": "linux-64",
  "installDir": ".pixi-sandbox/env",
  "tools": ["pixi", "cargo", "rustc", "clang-format", "clang-tidy"],
  "binDir": ".pixi-sandbox/env/bin"
}
```

Tools and agents read the receipt to verify environment state — never re-derive it.

## What the Pack Contains

Based on `pixi.toml` `[dependencies]`:

| Package        | Purpose                                |
|----------------|----------------------------------------|
| `rust` ≥1.96   | cargo, rustc, rustfmt, clippy-driver  |
| `cxx-compiler` | C++ compiler for cxx-build + cc        |
| `clang-tools` ≥22 | clang-format, clang-tidy           |
| `lefthook` ≥2.1 | Git hooks manager                     |
| `convco` ≥0.6   | Conventional commit checker           |
| `qgis` ≥3.44   | QGIS headers, libraries, plugins       |
| `pixi`         | Environment manager (for `pixi run` tasks) |

## Using Tools After Activation

Once `use-pack.sh` is sourced:

```sh
cargo build -p qgis-sys          # works — cargo on PATH
clang-format --version            # works — clang-tools on PATH
QT_QPA_PLATFORM=offscreen cargo test -p qgis-sys --test application_info -- --test-threads=1
```

**Note:** `pixi run <task>` may not work if the `default` environment wasn't pre-installed into the pack. Use the tools directly from PATH instead.

## GitHub Action (for downstream consumers)

Other repos that need the qgis-rs environment can use the pixi-sandbox action:

```yaml
- uses: Archont561/pixi-sandbox@v1
  with:
    pack: qgis-rs
    version: qgis-rs-linux-64
```

## Relationship to pixi.toml

The `pixi.toml` remains the single source of truth for environment definition. The env pack is a **pre-computed snapshot** of that definition — produced in CI, consumed where pixi can't install.

When `pixi.toml` or `pixi.lock` changes, the `env.yml` workflow triggers automatically (via `paths:` filter) and republishes the pack.
