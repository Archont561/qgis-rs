---
id: TASK-67
title: Publish QGIS product skills and add optional qgis-cli skills installer
status: To Do
assignee: []
created_date: '2026-10-10 13:47'
labels:
  - cli
  - rust
  - agents
  - skills
  - docs
milestone: m-3
dependencies: []
references:
  - crates/qgis-cli
  - py-packages/qgis-sdk
  - >-
    backlog/tasks/task-66 -
    Add-offline-agent-guides-and-capability-discovery-onboarding-to-qgis-cli.md
documentation:
  - AGENTS.md
  - .knowledge/decisions/D15-qgis-sdk-cli-pure-python-typer.md
priority: medium
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Outcome
Users and agents can list the supported QGIS product skills from an installed qgis-cli binary and explicitly install a selected skill through the external Skills CLI when bunx or npx is available. Ordinary GIS commands and offline skill discovery remain pure Rust and do not require Node or Bun.

## Approved public shape
- qgis-cli skills: print the product-skill catalogue and manual installation commands.
- qgis-cli skills --json: emit a deterministic machine-readable catalogue.
- qgis-cli skills add qgis-cli: install the GIS execution skill explicitly.
- qgis-cli skills add qgis-sdk: install the Python plugin-development skill explicitly.
- Installer options: --runner bunx|npx, --agent <name>, --yes, and --global.

Default to project-local installation in the current project. Prefer bunx when both runners are available; allow explicit override. Resolve runners from PATH only at installation time. A runner being present does not prove the Skills package is cached or that a remote skill is reachable: clearly disclose possible downloads, source/version, and target scope before invoking the child. If no usable runner exists, print exact manual commands and fail without installing a runtime. In non-interactive mode require --yes and an explicit --agent; do not hang on package-runner or Skills CLI prompts. Never silently select global scope or install every skill/agent.

## Product skill publishing
Maintain skills/qgis-cli/SKILL.md and skills/qgis-sdk/SKILL.md in this repository, with valid name/description frontmatter, focused workflow instructions, and declared tool compatibility. Keep them distinct from imported development skills under .agents/skills. Always install by an explicit catalogue skill name, not a repository-wide wildcard.

The qgis-cli skill checks the installed version, command help and runtime capabilities before choosing a workflow. Use the TASK-66 guide when that installed version supports it; otherwise use --help and existing discovery. Avoid copying a capability catalogue into the skill. The qgis-sdk skill covers the pure-Python plugin workflow and only shipped behavior, following D15; do not revive Rust SDK tooling or assume qgis-sdk has a guide command.

Use one embedded catalogue for names, descriptions, sources/refs, compatibility, and install arguments. Choose and record a tested Skills CLI version pin and a tested source-ref/version policy rather than silently executing an untested latest release. Source publication and remote installation verification require explicit push/publication sanction. Repository-based installation is the contract; skills find search-index inclusion is separate external evidence and must not be promised just because files exist.

## Boundaries and relationship to TASK-66
TASK-66 remains the offline guide, with no installer or automatic agent-file editor. This task owns product-skill publication and opt-in delegation to the external Skills CLI, not a reimplementation of that tool. It is not blocked on all of TASK-41 or on guide implementation: skills must handle versions without guide honestly.

Out of scope: automatic installations during startup/discovery, Node/Bun bootstrapping, arbitrary repository URLs or shell fragments as skill input, wildcard installation of imported repository skills, custom AGENTS.md/CLAUDE.md rewriting, a new MCP transport, new GIS capabilities, and mandatory Node/Bun dependencies for qgis-cli. Installation writes only through the delegated Skills CLI into the explicitly selected scope. Preserve existing guide/discovery/validation contracts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Publishable product skills exist at skills/qgis-cli/SKILL.md and skills/qgis-sdk/SKILL.md with valid metadata and compatibility guidance. They respect D15 and shipped commands, consult runtime help/capabilities rather than duplicating availability, and handle absent guide support. Explicit-name repository discovery/install instructions distinguish these skills from imported development skills.
- [ ] #2 qgis-cli skills and skills --json read one embedded catalogue offline, including names, purposes, source refs, compatibility and manual install instructions. JSON has a documented schema version and stable ordering. Listing works without Node/Bun/QGIS or a repository checkout, invokes no external process or network, and writes no files.
- [ ] #3 skills add accepts only a known catalogue skill plus documented options. It defaults to project scope, uses --global only when explicitly requested, and never passes a wildcard or installs all agents implicitly. Non-TTY execution without --yes or an explicit --agent fails clearly before spawning a child; invalid input is a documented usage error.
- [ ] #4 Runner selection is deterministic: explicit --runner overrides auto-detection; otherwise prefer bunx then npx from PATH. Missing or unusable runners produce actionable manual commands and a nonzero result without runtime installation. An explicit runner choice never silently falls back; a child failure never triggers a second installation attempt with another runner.
- [ ] #5 The installer delegates to a tested pinned Skills CLI version and explicit tested skill source/ref using process argument arrays, not interpolated shell commands. It discloses downloads and target scope, correctly handles paths/arguments containing spaces or metacharacters and platform executable resolution, and does not expose credentials or override telemetry opt-out settings.
- [ ] #6 Installation preserves child output on the appropriate streams, waits for completion, propagates ordinary child failure status, and documents wrapper launch errors and signal/cancellation mapping. --yes covers required runner and installer confirmations only after user opt-in. Failed or interrupted installation is never reported as success, and wrapper cancellation does not leave an installer running. JSON output is limited to listing unless a separate child-output contract is explicitly designed.
- [ ] #7 After agreeing public seams, red-green tests under crates/qgis-cli/tests/ use isolated cwd/HOME/PATH and fake runner processes to cover offline listing, both-runner preference, overrides, missing runners, unknown skills, scope and argument forwarding, noninteractive guards, successful/failed launches, nonzero child exits, and cancellation. Tests never download packages or modify real agent/user configuration; platform-specific gaps are recorded rather than claimed covered.
- [ ] #8 Documentation distinguishes guide instructions, live capabilities and installable skills, including optional network/filesystem effects, tested runner/Skills versions and exact per-skill manual commands. After publication is sanctioned, verify discovery and explicit-name installation from the actual published source in a disposable project and record versions/ref/evidence. Search-index visibility is checked separately when reachable; blocked or unpublished verification remains open.
- [ ] #9 Focused tests, cargo fmt/clippy and applicable pixi gates pass, preserving existing discovery/validation behavior and the no-default-features dependency boundary. No new external Rust dependency is required; repository automation, if needed, is an xtask subcommand with tests. No task acceptance criterion depending on remote publication or unsupported platforms is checked without evidence.
<!-- AC:END -->
