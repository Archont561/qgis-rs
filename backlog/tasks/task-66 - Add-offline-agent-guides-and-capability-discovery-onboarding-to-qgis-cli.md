---
id: TASK-66
title: Add offline agent guides and capability-discovery onboarding to qgis-cli
status: To Do
assignee: []
created_date: '2026-10-10 13:32'
updated_date: '2026-10-10 13:32'
labels:
  - cli
  - rust
  - agents
  - docs
milestone: m-3
dependencies: []
references:
  - crates/qgis-cli
  - crates/qgis-engine
  - docs/src/content/docs/cli/index.mdx
documentation:
  - AGENTS.md
  - .knowledge/decisions/D15-qgis-sdk-cli-pure-python-typer.md
priority: medium
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Outcome
An agent with only an installed qgis-cli binary can discover what to read, identify the commands actually supported by that build, and choose a safe non-interactive workflow without guessing flags or requiring a repository checkout.

## Reference and recommendation
The locally inspected Backlog.md 1.53.0 CLI provides instructions [guide] with --list, command-level --help, and agents --update-instructions for a short managed pointer in agent files. Adopt the progressive-disclosure pattern, not its project-management workflows or interactive installer.

Recommended public surface:
- qgis-cli guide: concise overview, topic index, and discovery-first workflow.
- qgis-cli guide --list: available topic IDs and summaries.
- qgis-cli guide <topic>: focused Markdown guidance.
- --json: stable structured output for the overview, index, or selected topic.
- qgis-cli <command> --help: exact syntax from clap.
- qgis-cli capabilities --json and doctor --json: existing live engine/backend reporting; guide does not probe QGIS or invent a second availability catalogue.

Start with overview, discovery, validation, and errors/safety topics. Explain version/capabilities/doctor, selecting command help, validating input, consuming JSON, handling exit codes, and refusing unavailable operations. Add further workflows only as their commands actually ship. Separate known protocol operations, callable engine routes, and parsed CLI commands; native engine support does not imply a CLI render/export/serve route works.

Use one authored, reviewed guide source embedded at build time and one topic registry. Keep the installed command independent of checkout files. Document a short optional AGENTS.md snippet directing agents to qgis-cli guide and runtime discovery; users copy it explicitly.

## Boundaries
This is a follow-up to TASK-41 discovery, already present in the tree, not a replacement or a dependency on every remaining TASK-41 slice. It need not wait for inspect/planning commands; it must describe only the shipped surface. D15 remains unchanged: GIS execution stays in Rust qgis-cli; plugin development stays in Python qgis-sdk.

Out of scope: a second instructions alias, automatic AGENTS.md/CLAUDE.md edits, an interactive setup wizard, a new MCP server or transport, implicit downloads/installations, new native capabilities, and new external dependencies. Future opt-in installer or MCP resource exposure should be separate work if requested.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The Rust CLI exposes guide, guide --list, and guide <topic> in top-level help. Successful reads exit 0; unknown topics and invalid options exit 2 with stderr diagnostics and no success document on stdout. Overview and selected topics are readable without ANSI decoration or a pager.
- [ ] #2 A documented --json contract includes a guide schema version, CLI version, stable topic identifiers and summaries, and Markdown content where applicable. Output is deterministic for the same binary and request, with exactly one JSON document on stdout and diagnostics only on stderr.
- [ ] #3 Guidance works offline from an unrelated working directory in a no-default-features build, without Python, Node, Qt, QGIS or WebEngine. Reading a guide never probes/initializes the native backend, prompts, writes files, modifies user/project configuration, or accesses the network.
- [ ] #4 Overview plus discovery, validation, and errors/safety topics teach only shipped behavior. They explain syntax-only CRS validation, validation exits 0/10/2 versus legacy exits, JSON stream separation, optional-backend doctor semantics, leading-minus argument handling, and the distinction between CLI parsing and engine/native availability. Pending commands and unimplemented execution paths are not presented as usable.
- [ ] #5 Topic enumeration and lookup use one authoritative registry and the binary embeds one maintained guide source. Command/flag facts come from clap where practical, live availability remains owned by existing engine discovery, and authored examples have drift coverage rather than a duplicate capability list or hand-edited generated copies.
- [ ] #6 CLI documentation includes a short copyable AGENTS.md pointer to guide and capabilities, explains the progressive-disclosure workflow, and links the new command from the overview/README. No automatic agent-file editing, extra alias, or installer is introduced.
- [ ] #7 After agreeing public seams, red-green integration tests under crates/qgis-cli/tests/ cover overview/index/topic selection, JSON schema and deterministic output, unknown topics/options, clean streams, unrelated cwd/isolated HOME, no helper runtimes, and no writes. Tests keep authored examples aligned with the parser and preserve existing discovery/validation behavior.
- [ ] #8 Focused pure tests, applicable native regression checks, cargo fmt/clippy, and pixi run gates pass, or exact environmental blockers are recorded. No new external dependencies or plugin-tooling behavior is added; any repository-wide automation belongs in xtask with tests.
<!-- AC:END -->
