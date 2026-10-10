---
id: TASK-64
title: Reconcile qgis-sdk knowledge docs and D13 with D15
status: In Progress
assignee:
  - '@me'
created_date: '2026-10-10 09:21'
updated_date: '2026-10-10 09:36'
labels:
  - qgis-sdk
  - docs
  - knowledge
  - decisions
milestone: m-5
dependencies: []
priority: high
type: docs
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Open item from the 2026-10-10 session 14 hand-off, re-scoped by measurement.

D15 makes the qgis-sdk CLI one pure-Python typer application, and D15 section 3 as amended by TASK-57 removes all Rust from qgis-sdk. Two knowledge documents and one published docs page still describe the retired design.

Measured, not assumed:

- .knowledge/qgis-sdk.md is a status draft specification with 72 rust mentions. Its section 2 (Rust Acceleration) and section 3 (Unified API, PyQGIS or Rust) document rust_accelerated, HAS_RUST and qgis_sdk.render, features, geometry and crs. None exist: zero code hits for rust_accelerated and HAS_RUST, and no render.py, features.py, geometry.py or crs.py in the package. The evidence table of that document already calls section 2 a specification owned by TASK-16, which D15 supersedes.
- The evidence table CLI row is affirmatively false: it names a Rust binary qgis-sdk at native speed and says the native CLI exists. crates/qgis-sdk and crates/qgis-sdk-core were removed in 2d8d69a.
- D13 carries an amendment banner and an updated enforcement table, but six places still describe the Rust CLI: the Context paragraph, the section 3 dependency graph (qgis-sdk-core to qgis-protocol, qgis_sdk._core to qgis-sdk-core), section 4, Consequences Accepted (plugin developers receive a Rust-native CLI), the Rejected alternatives no-fallback row that D15 reversed, and the Implementation gates list that names TASK-26 as live.
- docs/src/content/docs/getting-started/python-sdk.mdx line 24 tells users to print qgis_sdk.HAS_RUST, which raises AttributeError against the shipped package.
- docs/src/content/docs/guides/plugin-development.mdx lines 134 and 137 show rust_accelerated.

Out of scope, deliberately: README.md, docs getting-started/python.mdx, .knowledge/pixi.md and D07 mention maturin, which qgis-py legitimately keeps per D15 section 4. .knowledge/log.md entries and D14 are historical records and stay unchanged. D07 is a draft scope decision about Rust plugins rather than the SDK CLI, so superseding it is an architectural call for the owner; it is recorded as a question, not rewritten.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 .knowledge/qgis-sdk.md describes only what the package exports: no rust_accelerated, no HAS_RUST, no qgis_sdk render/features/geometry/crs modules, no rust init or rust build subcommand, no rust flag, no Cargo or PyO3 scaffolding; frontmatter title, description and tags match
- [ ] #2 The qgis-sdk.md CLI section lists the shipped typer commands and states the D15 section 2 prompt rule: questionary only at a TTY, every question answered by a flag, exit code 2 on a missing plugin name when non-interactive
- [ ] #3 The qgis-sdk.md evidence table names no Rust CLI and no archived task as an owner, and its test count claim matches a measured run
- [ ] #4 D13 Context, section 3 dependency graph, section 4, Consequences, Rejected alternatives and Implementation gates agree with D15 section 1 and section 3 as amended; no live text claims a Rust engine owns the qgis-sdk CLI
- [ ] #5 The published docs site no longer documents removed API in plugin-development.mdx and python-sdk.mdx, including the HAS_RUST snippet that raises AttributeError
- [ ] #6 Historical records stay unchanged (log.md entries, D14, completed task notes, and doc-7 which already carries a supersession banner), and a grep shows every removed identifier surviving only in a historical record, a test that pins its absence, or an explicit retirement note - never presented as available API
- [ ] #7 pixi run gates passes and the docs site still builds
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Retire the Rust specification rather than update it: D15 section 3 as amended rules the feature out and TASK-16 is archived, so sections 2 and 3 of qgis-sdk.md are deleted and the section numbering left intact by rewriting the Philosophy and Unified API prose to PyQGIS only. Then correct the CLI section against the shipped typer app, fix the evidence table rows that name a Rust binary and archived tasks, update the six stale places in D13, and fix the two published docs pages. Prove with a grep that the removed identifiers survive only in historical records.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10: worked. Ground truth was measured from the shipped package rather than inferred, and every claim below was checked before it was written.

Measured: the CLI exposes new, validate, info, version, build, package, test, install, dev, publish, bootstrap, vendor, plus the ui and bridge groups. build takes only --output/-o; there is no --rust and no --all-targets. package takes --output, --bundle and --offline-wheel. dev takes --launch and is not implemented. publish takes --zip and --dry-run and is not implemented. new takes name, --type general|processing|provider|server, -o/--output, --web, --framework vanilla|react|vue|webcomponents|bun, --declarative, --bun, --bundle, --offline-wheel, --ui/--no-ui, --author and --email. qgis_sdk.__all__ exports 145 names. METADATA_FIELDS has 20 entries. pyproject.toml declares the setuptools backend, typer and questionary, and the console script qgis-sdk = qgis_sdk.cli:main; the conda recipe pip-installs the same pure-Python package with --no-deps and declares the same entry point.

Scope corrections found while working:

1. Sections were retired in place rather than deleted and renumbered, which deviates from the recorded plan. The reason is that doc-1, the knowledge-to-backlog migration map, cites this document by section number (sections 1-4, 5-6, 7-8, 9-11, section 12), and so does the section 12 evidence table. Renumbering would have broken both. Each retired section keeps its number and states what was removed and by which decision, so a reader searching for rust_accelerated finds the reason rather than silence. Rust mentions in the file went from 72 to 29, and the remainder are those retirement notes.

2. Section 6 documents a plugin.toml format that does not exist at all. scaffold.py writes metadata.txt directly and nothing in the package reads a plugin.toml. Only the [plugin.rust] block was in scope for D15, so that block is removed and a banner now says the rest is a design proposal owned by TASK-3. Rewriting the whole config spec is not this task.

3. Section 12 named two pixi tasks, sdk-test and sdk-doctor, that do not exist in pixi.toml. Replaced with the invocation that does run: bun x turbo run test --filter=qgis-sdk-py, measured at 490 passed, 3 skipped, 8 deselected.

4. AGENTS.md documented bun x turbo run test --filter=qgis-sdk, which resolves to nothing: turbo answers No package found with name qgis-sdk in workspace. The package is qgis-sdk-py. One line fixed, because a house-rules document that cannot be run wastes the next session.

5. doc-7 needed no change. It already carries a supersession banner and every remaining mention is marked (retired) or (Superseded by D15).

6. The published docs pages were far more stale than the two lines the opening grep suggested. python-sdk.mdx had eight separate Rust claims, including a Rust-native CLI, both packages ship Rust binaries, a bin/ tree listing qgis-sdk twice as a Rust binary and an alias, and a conda recipe that builds Rust binaries. plugin-development.mdx had a whole Rust Acceleration section plus two frontmatter/intro claims. All corrected.

Not changed, recorded instead:

- TASK-43 is live and To Do, and its description and AC5 reference qgis_sdk._core as optional tooling. That extension no longer exists, so AC5 is vacuous for that clause. Amending a live task contract was not sanctioned this session, so it is reported for an owner decision.
- D07 is a status draft scope decision about Rust QGIS plugins via PyO3. D15 rules Rust out of the SDK, but whether a plugin may still ship its own Rust extension is a different question that D15 answers only in passing (a plugin that wants Rust runs cargo itself). Superseding or reaffirming D07 is an architectural call for the owner, not docs reconciliation.
- plugin-development.mdx still shows qgis-sdk publish as though it uploads; the command exits non-zero and says it is not implemented. Left alone as out of scope for D15, and worth folding into TASK-17.
- python-sdk.mdx still offers conda install -c conda-forge qgis-sdk. Whether the package is actually published to conda-forge is not verifiable from this sandbox, so the claim was left as found.

The gate caught a regression this task introduced. The first draft of section 5.1 named the retired command literally, and pixi run xtask check-sources failed with retired name: .knowledge/qgis-sdk.md. It is reworded to describe the alias without spelling it. The check allowlists backlog/, .knowledge/decisions/, .knowledge/log.md and CHANGELOG.md as history, which is why D13 and the archived task notes may still name it.
<!-- SECTION:NOTES:END -->
