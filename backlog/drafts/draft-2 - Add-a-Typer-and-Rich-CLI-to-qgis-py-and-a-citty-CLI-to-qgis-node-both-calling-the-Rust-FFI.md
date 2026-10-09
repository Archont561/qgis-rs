---
id: DRAFT-2
title: >-
  Add a Typer and Rich CLI to qgis-py and a citty CLI to qgis-node, both calling
  the Rust FFI
status: Draft
assignee: []
created_date: '2026-10-09 21:07'
updated_date: '2026-10-09 21:08'
labels:
  - qgis-py
  - qgis-node
  - cli
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reverses the built-in CLI removal from this session for these two packages. The CLI is a thin client: every answer comes from the Rust engine through the existing single invoke call, never from a parallel implementation.

Scope:
- qgis-py: a Typer app, presentation with Rich (tables, errors, progress). Installed as the qgis-py console script. Typer and Rich are the only new Python dependencies.
- qgis-node: a citty command tree, bin entry qgis-node. citty (0.2.2) is the only new JavaScript dependency for the CLI.
- Both CLIs expose the same command set, mapped to engine operations: version (engine_info), info (project_info), tiles --dry-run (plan_tiles), and extent describe (describe_extent). render stays out until the QGIS render path is confirmed in both bindings.
- Each command has a --json flag that prints the engine response unchanged.

Constraints:
- No Python-side or JS-side arithmetic, parsing or validation beyond argument plumbing. Anything with an answer goes to the engine.
- crates/qgis-cli (standalone binary) is untouched. The D13 boundary rules still apply: qgis-py and qgis-node must not depend on the qgis-cli crate.
- Do not add other dependencies, and no BDD or test-framework additions.
- The no-cli guard tests added this session (test_no_cli.py, no-cli.test.js) are replaced by positive CLI tests in the same commit as the feature.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 qgis-py ships a Typer app as the qgis-py console script; version, info, tiles --dry-run and extent describe each call invoke and print the engine answer
- [ ] #2 qgis-py output uses Rich for tables and errors; --json prints the engine response unchanged
- [ ] #3 qgis-node ships a citty command tree as the qgis-node bin with the same four commands, each calling invoke through the existing client
- [ ] #4 qgis-node --json prints the engine response unchanged; citty is the only new JS dependency
- [ ] #5 An engine refusal exits non-zero and shows its kind in both CLIs; no English error text is matched
- [ ] #6 Positive CLI tests in both packages: CliRunner for qgis-py, node test runner for qgis-node; the no-cli guards are removed in the same commit
- [ ] #7 No Python or JS arithmetic beyond argument parsing; a check or test proves the CLI reads answers from the engine
- [ ] #8 Gates pass; docs and both READMEs describe the CLIs
<!-- AC:END -->
