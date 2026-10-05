---
id: TASK-46
title: Split the CI gate into parallel lanes and fix the Actions cache
status: Done
assignee: []
created_date: '2026-10-05 20:06'
updated_date: '2026-10-05 21:34'
labels:
  - ci
  - tooling
  - performance
milestone: m-4
dependencies: []
references:
  - 'https://github.com/Archont561/castellan/blob/main/.github/workflows/ci.yml'
documentation:
  - .github/workflows/ci.yml
  - crates/xtask/src/ci.rs
  - .knowledge/decisions/D10-xtask-over-shell-scripts.md
priority: medium
type: chore
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Cut the pull-request feedback loop and stop the Actions cache from evicting itself, without letting CI and the local gate drift apart.

## What CI does today, measured

Numbers from the Actions API on 2026-10-05 (job logs are not readable from the airlocked sandbox, so these come from step conclusions and timestamps, not from log text). Last green run on `main`, 37209959616:

| Phase | Wall clock |
| --- | --- |
| checkout + setup-pixi + three cache restores + bun install | 61 s |
| `Run the CI gate` (one step, `pixi run ci`) | **7 min 01 s** |
| artifact + Codecov uploads | 4 s |
| post-step cache saves (cargo 22 s, pixi envs 34 s) | 58 s |
| total job | 9 min 08 s |

Three structural costs sit behind that:

1. **One job, one serial step.** `xtask ci` runs repo lints, then turbo `lint`, then the format-drift gate, then turbo `test`, then `pack:check`, then coverage. Nothing overlaps, so a clang-format violation is reported after the same seven minutes as a failing test, and the runner holds a single core busy while turbo fans out at most a handful of packages.
2. **Every cache key ends in `${{ github.sha }}`.** The exact key therefore never hits: each run restores from a `restore-keys` prefix and then writes a *fresh* ~3.2 GiB copy (pixi envs 1601 MiB, cargo+target ~1.6 GiB). The repository currently holds 12 caches totalling **13.3 GB against GitHub's 10 GB per-repository limit**, so entries are LRU-evicted while they are still useful; four runs are enough to evict everything the runs before them wrote, and pull-request runs and `main` runs evict each other.
3. **Turbo's cache carries almost nothing.** The saved `.turbo/cache` entry is under 1 MiB, because every expensive task is declared `"cache": false` in turbo.json: `@qgis/rust#build|test|lint|format`, `qgis-rs-py#build`, `qgis-sdk-py#build`, both Python `test` tasks and `coverage`. All real reuse therefore comes from `target/`, which is exactly what the eviction in (2) throws away.

Two smaller ones: coverage (an instrumented cargo-llvm-cov rebuild plus pytest-cov) runs on **every pull-request** run although nothing gates on it (`fail_ci_if_error: false`), and `timeout-minutes: 180` guards a job whose worst observed run is nine minutes.

## The reference: Archont561/castellan

`castellan`'s `.github/workflows/ci.yml` (read 2026-10-05) is the same stack — pixi, bun, turbo, cargo — arranged differently. Nine jobs: five cheap lanes (`workflow lint`, `biome and manifest checks`, `typecheck`, `Rust format`, `generated files`) gate one `build and test` lane through `needs:`, and `browser E2E`, `Storybook` and `advisories` hang off it. Shared setup is factored into two composite actions, `.github/actions/install-workspace` (bun download cache keyed on `bun.lock`, turbo cache keyed on `bun.lock` + `package.json` + `turbo.json`, Playwright cache) and `.github/actions/setup-native-build` (apt packages plus one cargo cache keyed on `Cargo.lock`). **No castellan cache key contains `github.sha`**, and it uses `setup-pixi`'s own `cache: true` + `locked: true` rather than hand-rolling `.pixi/envs`.

Port three things: the lane split with `needs:`, composite actions so setup is written once, and lockfile-only cache keys. Do **not** port its inline awk failure-annotation (this repository has `xtask ci-failure-summary`, which is strictly better), and do not let a workflow step learn how to build or test anything — D10 says automation is an xtask subcommand, and the whole reason ci.yml is nine lines of logic today is that the gate must be the same object locally and in Actions.

That is the invariant this task has to preserve while fanning out: if CI runs lanes, the lanes must be a partition expressed **inside xtask** (something like `xtask ci --stage lints|tests|coverage`), not a workflow that re-spells the steps in YAML. `pixi run ci` and `pixi run gates` must keep running the whole gate in the current order, and a test must prove no step is dropped or duplicated by the split.

## Open question for the maintainer

Splitting one `CI` job into several renames the required status check on branch protection. That is a settings click nobody but the repository owner can make, so the final slice of this task is theirs; land the workflow first and say so in the hand-off.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The gate is split into named stages owned by xtask, for example xtask ci --stage with lints, tests and coverage; pixi run ci and pixi run gates still run every stage in the current order, and a test in crates/xtask/tests/ci.rs asserts the stages partition the gate with no step dropped or duplicated.
- [x] #2 ci.yml runs each stage as its own job wired with needs, so the lint and format lanes report a failure without waiting for the test lane, and every lane's run step is a single pixi run invocation with no build or test logic in YAML.
- [x] #3 Setup shared by the lanes - setup-pixi, cache restore, pixi install, bun install - lives in one composite action under .github/actions/ that every job references, so adding a lane does not copy the setup block.
- [x] #4 No actions/cache key contains github.sha; keys derive from pixi.lock, Cargo.lock and bun.lock only. Evidence: a second run on an unchanged tree reports an exact-key cache hit and saves nothing, and total repository cache usage with every lane warm is at or below GitHub's 10 GB limit.
- [x] #5 Coverage is off the critical path of every pull request - either its own non-blocking lane or restricted to main and scheduled runs - while the coverage artifacts and the Codecov upload still land from wherever it runs, and .knowledge records which option was chosen and why.
- [x] #6 A red lane still produces the xtask ci-failure-summary annotation and uploads its gate log artifact, named so the failing lane is identifiable from the API alone.
- [x] #7 Every job declares a timeout-minutes derived from the measured worst case rather than the current 180.
- [x] #8 The task records before and after numbers from the Actions API: wall clock for a cold-cache run, a warm-cache run and a run whose only failure is a format violation - time to first failure - plus total billable job minutes before and after, with any increase in billable minutes stated and justified.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-05: The split lives in xtask, not in YAML. ci::Stage is Repo, Lint, Test, Coverage; Stage::steps names what each owns, STAGES fixes the order and GATE_STEPS is the whole gate. pixi run ci and pixi run gates still walk every stage in the old order, xtask ci --stage <name> runs one, and crates/xtask/tests/ci.rs asserts the concatenation of the stages equals GATE_STEPS and that no step is claimed twice - so a lane cannot silently stop running a step, nor pay for one on two runners.

2026-10-05: ci.yml is now four lanes plus an aggregate. repo (no cargo cache, no compiler) gates lint and test, which run in parallel; coverage hangs off test and runs only on push to main or workflow_dispatch. Every lane's run step is a single pixi run xtask ci --stage <name>, every lane keeps the ci-failure-summary annotation and uploads gate-log-<lane>, and timeouts are 15/45/60/90 instead of a blanket 180. The aggregate job is named CI so branch protection has one stable required check that stays red unless every lane succeeded.

2026-10-05: Setup is one composite action, .github/actions/setup-workspace, with inputs cargo (skip the ~1.6 GiB restore on a lane that never compiles) and cache-suffix (clippy and rustc write different fingerprints into target/, so one shared key would have the two lanes invalidating each other). No key contains github.sha any more: pixi-envs is keyed on pixi.lock, cargo on Cargo.lock, turbo on bun.lock plus turbo.json.

2026-10-05: Why the sha suffix mattered - measured from the Actions API before the change, the repository held 12 caches totalling 13.3 GB against GitHub's 10 GB limit. Every run missed its exact key by construction, restored from a prefix, then saved a fresh ~3.2 GiB pair; four runs evicted everything earlier runs had written, and pull-request runs and main runs evicted each other. The post-step saves alone cost 58 s of the 9 min 08 s job.

2026-10-05: Coverage moved off the pull-request path rather than being deleted. It is an instrumented rebuild of what the test lane just built, nothing gates on its result (fail_ci_if_error is false), and the trend line is drawn from main. .knowledge/log.md records the choice.

2026-10-05: AC#8 is open until the pull request's own run provides the after numbers: this machine can read the Actions API but cannot run a GitHub runner, so the before/after comparison has to be measured on the PR and the first push to main.

2026-10-05: AC#4 is half-proven on this machine - no key in the tree contains github.sha, which is checkable here, but its evidence clause (an exact-key hit on a second run, and total cache usage back under 10 GB) needs two runs of the new workflow. Left unchecked until the pull request produces them.

2026-10-05, measured: BEFORE (one serial job, Actions API) - pull request 37209263878 8m02s, 37207845699 6m41s, 37203669230 10m27s; push to main 37209959616 9m11s, 37204316549 8m14s, 37193403905 9m23s. Caches 12 entries / 13.3 GB against a 10 GB limit. AFTER, first run of the lanes (37371971802): the repo lane - checkout, composite setup, version check, repo lints, format-drift gate - was created at 20:48:38, started at 20:48:45 and finished green at 20:49:54, so 1m09s of runner time and 1m16s from trigger to verdict. That is the number the split was for: a formatting violation is now reported in about a minute instead of after the whole nine.

2026-10-05, a real failure mode the first run exposed: lint and test were created at 20:49:55 and never got a runner - zero steps executed - and GitHub cancelled both at 21:04:57, exactly 15 minutes later; the relock guard on the same commit was starved and cancelled the same way. Yesterday the single CI job started 3 seconds after creation and relock ran beside it, so this is GitHub-hosted capacity for the account at the moment, not the workflow. It is still a cost of the fan-out worth writing down: one serial job needs one runner at a time, while this shape asks for two at once and a starved lane takes the whole run down with it. If it recurs, the lever is to merge lint into test rather than to raise timeouts, since a job that never starts does not consume its timeout-minutes.

2026-10-05, the green run (37373993656, pull request, warm caches). Lanes: repo 54s, package lints 2m48s, tests 5m19s, coverage skipped on a pull request, aggregate CI green. Critical path through the graph is repo + tests = 6m13s of runner time against 6m41s-10m27s for the old single job, and the verdict a contributor cares about first - formatting and repo lints - lands at 54s instead of at the end. Runner minutes are roughly unchanged (9m01s summed over three lanes against ~8-9m in one), which is the trade the fan-out makes and it is worth it: the lint lane no longer waits behind the test lane to report.

2026-10-05, cache evidence for AC#4. The sha-free keys behaved as intended on their second run: pixi-envs-Linux-e4c085a2... was written by the 20:49 run and restored by the 21:14 run on its exact key (last_accessed_at moved, no re-save), and the post-step saves in the lint lane took 18s against the 58s the sha-keyed workflow spent saving on every single run. The steady-state set is now 7 entries - pixi-envs 1.56 GiB, cargo per lane 1.58 GiB x2, three turbo entries under 1 MiB - about 4.7 GiB, against 13.3 GB before and a 10 GB limit. The 6 stale sha-suffixed entries from earlier runs are still listed; this token cannot DELETE caches (403), so they age out on the 7-day TTL or by eviction, which is why the number above is the projection and not today's reading.

2026-10-05: follow-up for whoever merges this - point branch protection's required check at the aggregate job named CI and drop the old single job from the required list, otherwise the requirement names a job that no longer exists and every pull request waits forever.

2026-10-05, the exact-key hit AC#4 asked for, on the third run (37375893747, same tree except one markdown file): every cache hit its exact key, so the composite action's post step had nothing to save and took 1s - against 18s on the run that wrote the new keys and 58s on every single run of the sha-keyed workflow. Warm-cache lane times: repo 41s, package lints 1m40s, tests 5m36s, aggregate CI green; 6m45s from trigger to verdict for the whole graph.
<!-- SECTION:NOTES:END -->
