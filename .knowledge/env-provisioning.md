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
  - id: pixi-sandbox-configuration
    resource: https://archont561.github.io/pixi-sandbox/reference/configuration/
    title: "pixi-sandbox — Configuration Reference (incl. the [workflow] policy table)"
    author: human:archont561
  - id: pixi-sandbox-ci-publishing
    resource: https://archont561.github.io/pixi-sandbox/guides/ci-publishing/
    title: "pixi-sandbox — CI Publishing (policy in config, upgrade job)"
    author: human:archont561

---

# Environment Provisioning

## The Problem

qgis-rs requires a complex conda-forge environment: QGIS ≥3.44, Rust ≥1.96, clang-tools ≥22, cxx-compiler, lefthook, and convco. Normally this is solved by `pixi install` — but in sandboxed machines, **conda-forge, prefix.dev, and static.rust-lang.org are all unreachable**.

The only reliable network path is `github.com` over the git protocol. This is the same constraint class that [pixi-sandbox](https://github.com/Archont561/pixi-sandbox) was designed to solve.

## The Solution: pixi-sandbox

[pixi-sandbox](https://github.com/Archont561/pixi-sandbox) packages entire conda environments as a git transport (raw `.conda` files, helper tools, optional cargo vendor), distributes it via orphan git branches, and restores it offline. The consumer needs only `sh`, `git`, and `sha256sum`.

qgis-rs is a **consumer** of pixi-sandbox (release mode): it does not vendor the pixi-sandbox crate. The reviewed publish plan lives in `pixi-sandbox.toml` at the repo root.

### Producer (CI)

The `.github/workflows/publish-sandbox.yml` workflow drives the pixi-sandbox publisher. The file is **generated** — `pixi-sandbox init` writes it, `.github/workflows/relock.yml` and `scripts/restore.sh` with it, and `init --check` renders the three fresh and reports drift without writing. See [Regenerating the owned files](#regenerating-the-owned-files) for the exact invocation this repository is generated with.

On a push to `main` that changes one of the snapshot's inputs (the allowlist in `pixi-sandbox.toml`, below), on the weekly `schedule:`, or on `workflow_dispatch`, it:

1. Installs the pinned CLI with `pixi global install --channel https://prefix.dev/archont561/archont561 --channel conda-forge "pixi-sandbox==0.5.2"`, then validates `pixi-sandbox.toml` via `pixi-sandbox plan --json`.
2. Expands the plan into one native job per (bundle × platform) — here the single `developer` bundle (environments `default` + `bun`, platform `linux-64`).
3. On each native runner: downloads the checksum-verified v0.5.2 standalone release binary, `pixi install --frozen -e <env>` → `pack` → `doctor --verify` → `publish` (one orphan branch, force-pushed).
4. The same checksum-verified standalone release binary is embedded as the branch bootstrap executable.

v0.5.2 fixes the verification step itself: v0.4.3–v0.5.1 piped the `SHA256SUMS` line straight into `sha256sum --check`, which resolves the *filename* in that line against the runner's cwd — a name that does not exist there, so the check passed without ever reading the downloaded bytes. The step now rewrites the name to the download path and fails loudly on mismatch.

v0.4.0 **retired** the v0.3.x composite `Archont561/pixi-sandbox/setup` and `…/publish` actions (pixi-sandbox#47): the CLI now installs from its own conda channel into pixi's *global* environment, and the pack/verify/publish step runs inline in the workflow. There is no `Archont561/pixi-sandbox/*` action reference left to pin. Consumer workflows must also not build pixi-sandbox from the checkout — the checked-out tree belongs to the consumer project — which is why the pack step downloads the released binary and uses *that*.

The plan file is named `pixi-sandbox.toml`, not `.pixi-sandbox.toml`: `init` prefers the un-dotted name and only falls back to the dotted one for a pre-v0.4.0 checkout. `plan` still defaults to the dotted path, so both the generated workflows and `.github/workflows/ci.yml` pass `--config pixi-sandbox.toml` explicitly.

v0.4.3 also generates a second workflow, `.github/workflows/relock.yml`: a lock guard (`pixi lock --check`) that reports drift on every pull request, and a relock bot that runs `pixi lock` + `cargo fetch` and pushes the lockfiles when — and only when — the guard failed, refusing loudly on fork pull requests whose token cannot write.

The plan is consumed as `strategy.matrix.include: ${{ fromJSON(...).include }}`. This preserves the object shape GitHub Actions requires while selecting the plan's `include` array; v0.3.1 passed that array as `strategy.matrix` itself, so the plan succeeded but no publish job was instantiated (pixi-sandbox#37).

The branch published is `sandbox/developer-linux-64`. Packing, verifying and publishing all run on the *same* native runner — the payload never travels as an artifact.

`pixi-pack` / `pixi-unpack` are **not** local dependencies: the release binary fetches them from its own embedded SHA-256 pins, so the checked-in `pixi.lock` does not need to carry pack tooling.

### Regenerating the owned files

`pixi-sandbox` discovers `pixi-<command>` on `PATH`, so after the global install above:

```sh
# The same arguments the generated upgrade job passes to `init --check`.
pixi-sandbox init \
  --github-workflow-path .github/workflows/publish-sandbox.yml \
  --relock-workflow-path .github/workflows/relock.yml \
  --relock-ci-workflow ci.yml \
  --script-path scripts/restore.sh \
  --config pixi-sandbox.toml \
  --branch sandbox/developer-linux-64

# Drift check — writes nothing, exits non-zero naming each drifted file.
pixi-sandbox init --check <same arguments>
```

Pass every path explicitly rather than leaning on the defaults: `init`'s default
launcher is `restore.sh` at the repository root, and this repository's launcher lives
under `scripts/`. `--relock-ci-workflow` names the workflow the relock bot dispatches
after pushing a lock commit, relative to `.github/workflows/`. Files carrying the
generation marker are rewritten without `--force`; `--force` is only for a file
someone has taken over. The scheduled `upgrade` job performs exactly this
regeneration against the paths above and opens a pull request with the three owned
files, never touching `pixi-sandbox.toml` — reviewed data is never rewritten by a
tool.

### Generated-publisher policy lives in the config, not the file

This repository carried its policy as a list of hand edits, re-applied after every
regeneration, listed under a `LOCAL EDITS` banner in the workflow header. Commit
`0d8f9e7` regenerated the file against v0.5.1 and lost edits 1–5 without reporting
it; `d11e72e` reinstated all seven by hand, and `45ac2b5` repaired the publish
bootstrap's checksum step on top. An optional `[workflow]` table in
`pixi-sandbox.toml` carries the same policy, and `init` renders it — so
regeneration reproduces the workflow exactly, and no local edit is left to disagree
with the generator:

```toml
[workflow]
push_paths = ["pixi-sandbox.toml", "pixi.toml", "pixi.lock"]   # see below
permissions = true            # edit 2; default false
pixi_version = "v0.81.0"      # edit 5; default unset — setup-pixi resolves its own
setup_pixi_cache = false      # edit 5; already the default once [workflow] exists
[workflow.concurrency]
group = "publish-sandbox"     # edit 3; default unset
cancel_in_progress = false
[workflow.timeouts]
plan = 15                     # edit 4; timeout-minutes, default unset
publish = 120
```

Two fields move the moment the table exists **at all**, even empty:
`setup_pixi_cache` defaults to `false` (pixi-sandbox owns the native pixi install
while packing, so a cache keyed on the consumer manifest can restore a solve the
pack will not reuse), and `push_paths` defaults to a derivation — the sandbox config,
`pixi.toml`, `pixi.lock`, plus whichever of `package.json`, `bun.lock`,
`Cargo.toml`, `Cargo.lock` exist. `plan --json` surfaces that derivation under its own
`push_paths` key, so the list the next `init` would write can be diffed first.
Everything else is opt-in per key, and `permissions = true` narrows the workflow to
`contents: read` with `write` regained by the publish job alone.

This repository sets `push_paths` explicitly, because the derivation is a superset of
what this snapshot actually packs:

| Path | Why it is an input |
|------|--------------------|
| `pixi-sandbox.toml` | the plan — environments, platforms, `cargo_vendor` |
| `pixi.toml`, `pixi.lock` | what the packed conda environments contain |
| `Cargo.toml`, `Cargo.lock` | the `cargo vendor` tree |
| `crates/*/Cargo.toml` | member manifests; the root `Cargo.toml` path alone would miss them |
| `.github/workflows/publish-sandbox.yml` | the generator stamps its own version into the workflow |

Deliberately **not** included, unlike the old hand edit: `package.json` / `bun.lock`,
`ts-packages/**` and `py-packages/**` (the transport is conda environments, pinned
tools and `cargo vendor` — it carries no `node_modules`, so a JS dependency bump
cannot change a packed byte, and the Python distributions are developed in place with
`maturin develop` rather than packed), plus `crates/*/build.rs` (`cargo vendor`
resolves the dependency graph, not what a build script compiles). The old list also
named `ts-packages/qgis-node/Cargo.toml`, `ts-packages/qgis-node/build.rs` and
`ts-packages/qgis-node/package-scripts/**` — paths that stopped existing when
`packages/` was split into `crates/`, `ts-packages/` and `py-packages/` (`c569e12`),
which moved the napi crate to `ts-packages/qgis-node/src-rust`.

The relock bot needs no path either: a `GITHUB_TOKEN` push starts no workflow, so it
dispatches `publish-sandbox.yml` explicitly after pushing a lock commit.

Three things in the old hand-edited workflow are **not** expressible in `[workflow]`,
and the generated file gives them up deliberately:

- `timeout-minutes` on the `upgrade` job. `[workflow.timeouts]` covers `plan` and
  `publish` only; the upgrade job runs a download, three renders and a `gh pr create`,
  and the six-hour default costs nothing.
- A second, per-branch `concurrency` group on the publish job
  (`sandbox-publish-<repo>-<branch>`). The workflow-level group already admits one run
  of the workflow at a time, which is the stronger form of "a rerun cannot race an
  in-flight publish"; with one bundle on one platform the per-branch refinement
  changes nothing.
- Dropping the `Install pixi-sandbox CLI` step from the publish job. It is redundant
  there — the downloaded standalone binary runs `pack`/`doctor`/`publish` — but it
  costs one channel install and keeps the file free of hand edits. The step is
  *required* on the plan job, which calls `pixi-sandbox plan` off `$PATH`.

Edit 6 (the repaired `SHA256SUMS` check) needs no config at all: v0.5.2 generates it,
and generating it is the whole reason this repository can drop the `LOCAL EDITS`
banner the `d11e72e` header warned every reviewer about.

### Consumer (sandbox / local)

As of v0.3.1 the transport is **git-only**: the restore script never touches the
network and never sources an env script. The branch has to be present locally or
under `origin/` first, which is the one step that still needs a remote.

```sh
# From any machine with sh + git (no pixi, no conda):
git fetch origin sandbox/developer-linux-64
scripts/restore.sh
# default branch: sandbox/developer-linux-64, derived from pixi-sandbox.toml
# default output: .
```

`scripts/restore.sh` is generated by `pixi-sandbox init` (it lives under
`scripts/`, so it resolves the repo root with `git rev-parse --show-toplevel`
rather than assuming the caller's cwd). It reads `branch_prefix`, the bundle name
and the current platform out of `pixi-sandbox.toml`, resolves that to a branch ref
(falling back to `origin/<branch>`), `git archive`s the transport into
`.pixi/.restore-transport`, and hands that directory to the `pixi-sandbox
restore` binary the branch itself carries. Override the branch with
`PIXI_SANDBOX_BRANCH`, or disambiguate between several bundles publishing the
same platform with `PIXI_SANDBOX_BUNDLE`.

`init` emits a launcher for **the platform it runs on** only, so running it on
Linux produces `restore.sh` and nothing else — there is no committed
`scripts/restore.ps1` in this tree. A Windows airlock generates its own by
running `pixi sandbox init --project-root . --script-path scripts/restore.ps1`
there. The two behaviours it has to keep in step with are: a missing local ref is
fetched shallowly unless `PIXI_SANDBOX_FETCH=skip` says the ref is already there,
and user-tool registration is selected by the `PIXI_SANDBOX_USER_TOOLS`
environment variable (`register` by default, `skip` for a locked-down host) rather
than by a flag — the binary being executed comes from the packed branch, which may
predate `--user-tools`, and an unknown *variable* is ignored where an unknown flag
is a hard error.

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
| `scripts/restore.sh`    | Generated airlock launcher: restore `default`/`bun` from an already-fetched sandbox branch |

A Windows airlock generates `scripts/restore.ps1` the same way; it is not
committed here because `init` only emits the launcher for the platform it runs
on.

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
git fetch origin sandbox/developer-linux-64
scripts/restore.sh
cargo build -p qgis-sys          # works — cargo on PATH (offline)
clang-format --version            # works — clang-tools on PATH
pixi --version                   # works — bundled pixi
QT_QPA_PLATFORM=offscreen cargo test -p qgis-sys --test application_info -- --test-threads=1
```

## Relationship to pixi.toml

The `pixi.toml` remains the single source of truth for environment definition. The sandbox transport is a **pre-computed snapshot** of that definition — produced in CI by the reusable publisher, consumed where pixi can't install.

The `publish-sandbox` workflow republishes the bundle only when a push to `main` changes one of the snapshot's inputs — the plan, the two Pixi manifests, the Cargo manifests including every member, or the workflow itself; other pushes leave the published branch untouched. The trigger is the `push_paths` table in `pixi-sandbox.toml`, rendered by `init`, and the Bun lockfile is deliberately absent from it: the transport packs conda environments, the pinned tools and `cargo vendor`, not `node_modules`. See [Generated-publisher policy lives in the config, not the file](#generated-publisher-policy-lives-in-the-config-not-the-file). The environments actually published are gated by `pixi-sandbox.toml` (explicit, reviewed bundles — never "every environment"), not by the manifest alone.
