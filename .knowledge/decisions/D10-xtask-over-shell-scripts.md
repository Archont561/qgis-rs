---
type: Decision
id: D10
title: Repository Automation as `cargo xtask`, Not Shell Scripts
description: "The gate, the lints, the scaffolder and the release pipeline become subcommands of a compiled, tested binary; pixi tasks stay the single entry point."
status: accepted
tags: [automation, ci, xtask, pixi, tooling]
date: 2026-10-03T00:00:00Z
---

# D10: Repository Automation as `cargo xtask`

## The Question

Repository-wide automation — the CI gate, the C++ and TOML lints, the npm
contents check, the `qgis-sys` scaffolder, the libqca repair, the CI failure
summary, the six-step release pipeline — lived in `scripts/*.sh`, called by path
from `pixi.toml`, `lefthook.yml`, three GitHub workflows and a `package.json`.

That is a dependency graph in which *none* of the callers can check that the
callee exists, takes the arguments being passed, or still does what the comment
above the call says it does.

## The Decision

**Repository automation is `crates/xtask`**, a normal workspace binary, reached
through one pixi task:

```bash
pixi run xtask ci [--no-coverage]
pixi run xtask check-cpp [files...]
pixi run xtask lint-toml  [files...]
pixi run xtask pack-check <package-dir> <required...>
pixi run xtask scaffold <layer> <concept> <QgisClass> <short_name>
pixi run xtask setup-qca
pixi run xtask ci-failure-summary <log>
pixi run xtask release <verify-version|prepare|build-artifacts|checksums|publish-crates|publish-github-packages>
```

`pixi run xtask …` is the entry point; `pixi run ci`, `gates`, `setup`,
`scaffold`, `check-cpp` and `lint-toml` remain as named aliases, because those
are the names a contributor, a hook and a workflow already type. A *new*
repository verb is a new subcommand and usually no new line in `pixi.toml` at
all.

### What stays out

**Per-package verbs stay with the package.** `build`, `test`, `lint`, `format`,
`coverage`, `typecheck` and `pack:check` are declared in each package's own
`package.json` and fanned out by turbo. xtask calls `turbo run <task>`; it does
not reimplement it. The command that builds a package must be in the manifest a
reader of that package already has open — otherwise the package is not portable
and the root becomes a second place to look.

**Bootstrap stays shell.** `scripts/restore.sh` runs on a machine with no
cargo; it cannot be a cargo binary. `scripts/version.ts` stays TypeScript: it
is the one tool that rewrites every manifest in the repository, it is already
the single source of truth, and `xtask release` shells to `pixi run version`
rather than owning a second implementation of it. The `rust-*.sh` / `py-*.sh`
files stay because they are package verbs, not repository verbs.

## Why

* **The arguments are checked.** clap parses them, `--help` is generated, and a
  typo in a workflow fails at the argument parser with a usage message instead
  of silently taking `$2` as empty.
* **The automation is linted and tested.** `cargo clippy -D warnings` covers
  xtask like any other crate, and `cargo test -p xtask` (16 tests, ~6s) covers
  the parts that are logic rather than process spawning: the publish order and
  exclusions of the crates.io list, the glob matching in `pack-check`, the
  needle filter in the failure summary, the scaffold templates' idempotent
  append. Nothing tested `ci.sh`.
* **One language.** This is a Rust repository. The gate was the only component
  written in the one language here with no compiler, no type checker and no
  test harness.
* **Composition instead of duplication.** `ci` and `gates` differ by a bool;
  `check-cpp` with and without a staged file list differ by a `Vec<String>`
  being empty. In shell these were separate files or separate `case` arms that
  drifted. (This mirrors the check/write pairs in `Archont561/pixi-sandbox`:
  one task with an argument, not twins.)
* **Errors say what to do.** `anyhow` context replaces `set -euo pipefail` plus
  a `trap`, so a failing step names the step, the command and the exit code.

## The Costs, Accepted

* **A compile before the first run.** ~6s cold for xtask itself in this
  workspace, cached afterwards. CI already has the cargo cache warm for the
  workspace build; locally this is noise next to a QGIS link step.
* **xtask needs cargo.** Which is exactly why bootstrap stays in
  `scripts/restore.sh`, outside pixi and outside cargo.
* **A shell one-liner is no longer the cheap option.** Deliberate: the cheap
  option is what produced eight untested files called by path from four
  manifests.

## Alternatives Considered

| Alternative | Why not |
| --- | --- |
| Keep `scripts/*.sh`, add `shellcheck` to the gate | Checks syntax, not arguments, not behaviour; still no tests, still four callers referencing a path |
| Inline the commands into `pixi.toml` | A multi-line command embedded in TOML is unreviewable, un-lintable and unrunnable outside the manifest — the original reason the scripts existed |
| `just` / `make` | A third tool with a third syntax to install and learn, and the recipes are still untyped, untested strings |
| A Python or TypeScript task runner | Both interpreters are already here, but neither is the language of the thing being automated, and both reintroduce "which environment is this running in?" |

## Consequences

* `crates/xtask/` exists: `main.rs` (clap dispatch), `ci.rs`, `lints.rs`,
  `scaffold.rs`, `release.rs`, `util.rs`. `publish = false`.
* Deleted: `scripts/{ci,check-cpp,lint-toml,npm-pack-check,scaffold,setup-qca,ci-failure-summary}.sh`
  and `scripts/release/*.sh`.
* `pixi.toml`, `lefthook.yml`, `ci.yml`, `autorelease.yml`, `release.yml` and
  the two npm `pack:check` scripts call subcommands instead of paths.
* `scripts/README.md` now documents only what is still shell, and why each one
  is an exception.
* The gate's step order is a value in `ci.rs`, so "what does CI run, in what
  order" is answered by reading one function.
