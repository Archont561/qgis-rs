---
id: TASK-59
title: Build the @archont561/qgis-sdk Node CLI with citty and @clack/prompts
status: To Do
assignee: []
created_date: '2026-10-09 15:47'
updated_date: '2026-10-10 09:22'
labels:
  - qgis-sdk
  - web
dependencies: []
priority: medium
type: enhancement
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The qgis-sdk bin is built with citty and offers create, build, types and package commands
- [ ] #2 Interactive prompts use @clack/prompts, and every prompt is skipped when its flag is given
- [ ] #3 The vanilla template uses bun build when bun is selected, and Vite with TypeScript otherwise
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Archived 2026-10-10 as superseded by D15 section 1 and D13 section 1, on the owner decision recorded in this session.

AC1 asks for a qgis-sdk bin built with citty offering create, build, types and package commands. D15 section 1 states that qgis-sdk is the only plugin-development command, that it is a Python console script calling qgis_sdk.cli:main built with typer, and that there is no native extension and no Rust CLI crate. D13 section 1 states that no second name exists for the plugin CLI, and D15 rejected keeping qgis-plugin as an alias precisely because a second name is the duplicate surface D13 was written to prevent. A Node plugin-tooling bin offering create, build and package would be a second implementation of the same four commands the Python CLI already owns, which is the drift D13 section 4 and the TRACKED_FALLBACKS rule exist to stop.

AC2 and AC3 are scoped entirely inside AC1: prompts for the citty commands, and the template build behaviour of the scaffolding those commands perform. They cannot be implemented without it.

The dependency cost is also ruled out. Measured today, @archont561/qgis-sdk declares no bin and no runtime dependencies, and neither citty nor @clack/prompts appears anywhere in the repository or in bun.lock. D15 section 5 states that typer and questionary are the qgis-sdk runtime dependencies and that no other dependency is added to qgis-sdk for the CLI. Adding two npm packages would also need a lockfile change this sandbox cannot make offline.

What is archived is the plugin-tooling CLI scope of this task, not the package. @archont561/qgis-sdk remains a legitimate product as the WebEngine and QWebChannel client per D13 section 1, and it keeps its 107 passing bun tests. If a Node-side scaffolding surface is ever wanted again it needs a new decision record that reconciles it with D15 section 1 first, not a task that assumes it.
<!-- SECTION:NOTES:END -->
