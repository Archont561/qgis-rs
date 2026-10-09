---
title: Release Model
description: "One version, one tag, one set of artifacts: how qgis-rs cuts a release across crates.io, PyPI, npm, GitHub Packages and prefix.dev."
---

# Release Model

Execution and release proof live in [TASK-21](../backlog/tasks/task-21%20-%20Cover-the-xtask-release-pipeline-with-an-end-to-end-dry-run.md); this document remains the release runbook and rationale, not a second release-status checklist.

Adopted from `Archont561/geoquery`, adapted to this repository's five publishing
surfaces. Two workflows and one binary (`pixi run xtask release <step>`,
`crates/xtask/src/release.rs`); nothing is published as a side effect of
merging.

## The two halves

| Workflow | Trigger | What it does |
| --- | --- | --- |
| `.github/workflows/autorelease.yml` | `workflow_dispatch` | `convco` derives the next SemVer from the conventional commits since the last `v*` tag; `xtask release prepare` writes it into every manifest, regenerates `CHANGELOG.md`, refreshes `bun.lock` / `Cargo.lock` / `pixi.lock`; the workflow commits `chore(release): vX.Y.Z` to `main` and tags it. |
| `.github/workflows/release.yml` | push of `v[0-9]+.[0-9]+.[0-9]+` | Verifies the tag against the manifests, re-runs the gate on the tagged commit, builds every artifact, then attempts each registry independently and always creates the GitHub Release. |

The commit is pushed **before** the tag on purpose: only a release commit that
`main` accepted may acquire the tag that triggers publication, so a
branch-protection rejection cannot leave a publishable tag on an unmerged commit.

## One version

`[workspace] version` in the root `pixi.toml` is the single source of truth. Not
`Cargo.toml`, and not `package.json`: pixi owns the toolchains, the environments
and the tasks, and every other manifest is downstream of it.

* Cargo crates inherit with `version.workspace = true` — a hardcoded version in
  a crate fails `version-check` as a *structural* fault, before any value
  comparison.
* `[workspace.dependencies].qgis-*` entries carry both a `path` and a registry
  `version`; cargo substitutes the latter when packaging for crates.io, so they
  are a published surface even though no build reads them.
* The wheels, the conda `[package]` tables, the npm packages and even the
  private facade `package.json` files restate it and are all compared.

`scripts/version.ts` is the reader, checker and writer
(`pixi run version` / `version-check` / `version-set X.Y.Z`). `version-check`
runs in the CI gate and in the `pre-push` hook, because a version mismatch is
the one failure that cannot be fixed after a release is cut.

## Builds block, registries do not

`xtask release build-artifacts` produces `dist/pypi`, `dist/npm` and
`dist/conda` before a single upload is attempted, and `xtask release checksums`
writes one `SHA256SUMS` over all of them. Each
registry step is then `continue-on-error: true` and its outcome is reported in
the job summary.

The GitHub Release is required and last. It holds the exact bytes whether or not
a third-party registry accepted its copy, so a maintainer can retry one service
from the same immutable tag. Do not give that step `if: always()` — a release
that failed to build must not produce an empty release.

## Credentials

Only crates.io needs a stored secret (`CRATES_IO_TOKEN`). prefix.dev, PyPI and
npmjs all use the job's OIDC identity, so before the first release:

1. PyPI — configure Trusted Publishing for both `qgis-py` and `qgis-sdk`:
   repository `Archont561/qgis-rust`, workflow `release.yml`, environment
   `release`.
2. npmjs — the trusted publisher must match the repository URL in the package's
   `package.json`, this workflow's filename, and the `release` environment.
3. GitHub Packages is a *separate* registry with no Trusted Publishing; it uses
   the workflow token written to a throwaway npmrc so it can never be applied to
   the npmjs upload.
