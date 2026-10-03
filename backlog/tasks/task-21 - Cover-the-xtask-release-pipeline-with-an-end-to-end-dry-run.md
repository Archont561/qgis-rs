---
id: TASK-21
title: Cover the xtask release pipeline with an end-to-end dry run
status: To Do
assignee: []
created_date: '2026-10-02 22:35'
updated_date: '2026-10-03 08:31'
labels: []
milestone: m-4
dependencies: []
documentation:
  - .knowledge/release.md
  - .knowledge/decisions/D10-xtask-over-shell-scripts.md
priority: medium
type: chore
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`crates/xtask` now owns the release steps that used to be `scripts/release/*.sh` (D10). Its unit tests cover the publish order, the exclusions and the pure helpers, but the steps that spawn cargo/maturin/npm are only exercised by a real tag. Add a `--dry-run` path (or a `release smoke` subcommand) that builds the artifact tree and the checksums without uploading, and run it in CI on pull requests so a broken release pipeline is caught before the tag exists.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 xtask release build-artifacts and checksums can run without any registry credentials
- [ ] #2 A CI job exercises that path on pull requests and uploads the resulting dist tree as an artifact
- [ ] #3 A missing artifact (an unbuilt wheel or tarball) fails the dry run
<!-- AC:END -->
