---
id: TASK-57
title: Make qgis-sdk a pure-Python PyQGIS plugin CLI with typer and questionary
status: Done
assignee: []
created_date: '2026-10-09 15:47'
updated_date: '2026-10-10 08:12'
labels:
  - qgis-sdk
dependencies: []
priority: high
type: enhancement
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 qgis-sdk is a pure-Python console script with no Rust, no _core and no pyo3 build
- [x] #2 The CLI never imports PyQGIS or qgis_py, and the plugin zip contains no qgis_sdk code
- [x] #3 questionary prompts cover the non-web scaffold choices, and every prompt has a flag for CI
- [x] #4 qgis-sdk package builds the plugin zip, and the test suite runs without QGIS
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Landed: qgis-sdk CLI has no rust subcommand, no --rust flag and no cargo call. scaffold_plugin lost with_rust. Package picks the plugin package by name and skips tests/dist/wheels, which fixed a bug where package wrote tests.zip.

Prompts: new asks name, --type, --ui/--no-ui, --author, --email only at a TTY. Each has a flag. Non-TTY with no name exits 2. Tests: tests/test_cli_task57.py (16 cases, pure layer).

Proof, measured: pixi pure layer 490 passed 3 skipped 8 deselected (was 474); qt 3; qgis 5. Bare venv with no QGIS (py3.12 venv, typer questionary pytest hypothesis, wheel built from this tree): 489 passed 4 skipped. The nested pytest11 failures recorded in session 13 did not reproduce because the wheel provides the entry point.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
CLI is pure Python on typer and questionary. Rust removed, prompts flagged for CI, package bug fixed (tests folder picked as plugin). Gate result is in the log entry.
<!-- SECTION:FINAL_SUMMARY:END -->
