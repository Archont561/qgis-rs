---
id: TASK-62
title: >-
  Derive version-set and version-check from one surface registry in
  scripts/version.ts
status: To Do
assignee: []
created_date: '2026-10-09 21:42'
labels:
  - tooling
  - refactor
milestone: m-0
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Audit finding (session audit, scope: this session changes). scripts/version.ts lists the same version surfaces twice: the check() surfaces array (around lines 184-206) and the setVersion() writes (around lines 254-292, with its own npm list and dist loop). The two lists are maintained by hand. Adding a surface to one and not the other means version-check silently fails to guard it, and nothing detects the mismatch. The session edit that removed the qgis-node platform packages had to change both lists.

Rule: clean-code core-dry. Keep each surface in one registry entry that both writing and checking consume.

Behavior to preserve: pixi run version-set and pixi run version-check produce the same files and the same pass/fail results for every surface today. This is a behavior-preserving refactor. It is not a change to which surfaces exist.

Scope: scripts/version.ts only. Non-goals: adding or removing surfaces; changing the semver rule; changing the cargo internal-dependency handling.

Test seam: check(startDir) and setVersion(version, startDir) already accept a root directory, so tests run against a fixture tree. Agree this seam with the user before writing tests.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Characterization tests on a fixture tree pin the current behaviour of setVersion and check: every surface is written, every surface is checked, and drift in each surface is reported, before any refactor
- [ ] #2 Writing and checking consume one surface registry; adding a surface requires one entry, and a test proves that a new entry is both written and checked
- [ ] #3 No duplicated surface list remains in scripts/version.ts; grep for the npm platform list finds nothing
- [ ] #4 pixi run version-check passes on the current tree after the refactor
- [ ] #5 Refactor changes are one small step at a time, each with the characterization tests green
<!-- AC:END -->
