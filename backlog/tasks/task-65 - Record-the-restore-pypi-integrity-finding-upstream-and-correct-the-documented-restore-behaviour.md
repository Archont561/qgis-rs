---
id: TASK-65
title: >-
  Record the restore pypi integrity finding upstream and correct the documented
  restore behaviour
status: In Progress
assignee:
  - '@me'
created_date: '2026-10-10 09:21'
updated_date: '2026-10-10 09:54'
labels:
  - environment
  - sandbox
  - docs
milestone: m-5
dependencies: []
priority: medium
type: chore
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Open item 1 from the 2026-10-10 session 14 hand-off. scripts/restore.sh exits 1 on its final tree check with 18 failures in the default environment dist-info. The environments work, so this was left as a note with no task and no root cause.

Root cause, measured this session and proven to a 1:1 correspondence:

- .pixi/.restore-work/pack-default/pypi holds exactly nine wheels: annotated_doc, markdown_it_py, mdurl, prompt_toolkit, questionary, rich, shellingham, typer and wcwidth. Those are exactly the nine failing packages.
- pixi-pack transports pypi packages as wheels, not as installed bytes. pixi-unpack therefore re-installs them with uv at restore time.
- uv writes dist-info/uv_cache.json containing a wall clock timestamp. The value found after this restore decodes to 2026-10-10T08:57:18Z, which is during the restore, and the file mtimes are 08:57:47.
- dist-info/RECORD embeds a sha256 line for uv_cache.json, so when that file changes RECORD must change too. Nine packages times two files equals the 18 failures.
- Only 9 of 62 dist-info directories in the default env carry uv_cache.json; the 53 conda installed ones verify clean. The bun env has no pypi packages and reported 76366 entries, 0 failures.

So the mismatch is deterministic by design and is not corruption. The per-file digest check cannot pass for files that the unpack step regenerates with a fresh timestamp.

The check is not in this repository. It is crates/pixi-sandbox-core/src/verify.rs in Archont561/pixi-sandbox, public and reachable, three open issues and none for this. pixi-sandbox restore exposes no exclusion flag. scripts/restore.sh is generated, and pixi-sandbox init refuses to overwrite edited generated files while a gate fails on drift, so the launcher cannot be hand-edited here.

Consequence worth recording: because restore exits non-zero it skips user tool registration, so pixi is never symlinked into the per-user bin directory and the next command in the documented sequence fails with command not found. The session skill documents the opposite.

Sanctioned by the owner this session: file the upstream issue and record the known limit in this repository. Patching pixi-sandbox itself is not sanctioned.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The root cause is recorded in .knowledge/env-provisioning.md with the evidence: the nine wheel names, the uv_cache.json timestamp mechanism, the RECORD embedding, and the 9 of 62 dist-info count
- [ ] #2 An issue is filed on Archont561/pixi-sandbox carrying a reproduction and the root cause, and its number is recorded in this task and in env-provisioning.md
- [ ] #3 The documented restore sequence in .agents/skills/session/SKILL.md no longer claims zero integrity failures, and states that a non-zero restore skips the pixi symlink so PATH must be set from .pixi/tools/linux-64
- [ ] #4 The known limit states plainly that the fix is upstream and that the environments are usable despite the non-zero exit, so a future session does not re-diagnose it
- [ ] #5 No generated file is hand-edited and pixi run gates still passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10: worked.

Filed upstream as Archont561/pixi-sandbox issue 128, carrying the reproduction console output, the versions, the measured root cause, the impact on user-tool registration, three suggested fixes ranked by size, and the consumer-side workarounds that were considered and rejected. The issue states that the fix belongs to pixi-sandbox because the check is crates/pixi-sandbox-core/src/verify.rs, which is not in this repository.

Root cause proven to a 1:1 correspondence rather than inferred. The kept work dir holds exactly nine wheels under .pixi/.restore-work/pack-default/pypi - annotated_doc, markdown_it_py, mdurl, prompt_toolkit, questionary, rich, shellingham, typer and wcwidth - and those are exactly the nine failing packages. pixi-pack transports pypi packages as wheels, so pixi-unpack re-installs them with uv at restore time. uv writes dist-info/uv_cache.json with a wall clock timestamp; the value found decodes to 2026-10-10T08:57:18Z, which is during this restore, and files installed in the same batch share it, which is why several packages report an identical got digest. dist-info/RECORD contains a sha256 line for uv_cache.json, so it must change too. Two files times nine packages equals the 18 failures. Only 9 of the 62 dist-info directories in default carry a uv_cache.json; the 53 conda installed ones verify clean, and the bun env has no pypi packages and reported 76366 entries with 0 failures.

Usability confirmed rather than assumed. pixi 0.81.0 answers, pixi run -- cargo --version answers 1.96.1, pixi run -- bun --version answers 1.3.11, typer 0.27.3 and questionary both import, bun-install restored 1086 packages offline in 2.25 s, pixi run gates exited 0, and turbo run test exited 0 with 12 of 12 tasks: Rust 323 plus 30, qgis-sdk-py 490 passed with 3 skipped and 8 deselected, qt 3, qgis 5, qgis-py-dist 18, bun 160, ctest 1 target at 100 percent.

Two documents were corrected because both described a restore that no longer happens. .knowledge/env-provisioning.md gained a Known limit subsection with the root cause and the issue link. Its Using Tools After Restore block was wrong in a second way that had nothing to do with the integrity bug: it showed cargo build and clang-format working directly, and measured on this sandbox neither is on a bare PATH, only pixi run -- cargo is. It also showed pixi --version working because the bundled pixi is on PATH, which is true only when registration ran. The maturin claim in the push_paths rationale now names qgis-py alone, since D15 section 4 moved qgis-sdk to setuptools.

.agents/skills/session/SKILL.md claimed the restore re-verifies the tree with 75732 entries and 0 failures and then symlinks pixi into the per-user bin. Both halves are false now, and the second costs real time: the non-zero exit skips registration, so the documented export PATH finds nothing and the next command dies with pixi: command not found. The paragraph is rewritten with measured numbers, the snippet links pixi explicitly before the export, and a bullet was added to Known limits of this machine so an agent skimming that list sees it. That skill is repo-owned: skills-lock.json lists seven skills and session, backlog and audit are not among them, so editing it cannot be reverted by a skills sync.

No generated file was hand-edited. git status is empty for scripts/ and .github/workflows/, so scripts/restore.sh and publish-sandbox.yml are untouched; the correction went into the knowledge doc and the repo-owned skill instead.

Separate pre-existing finding, not caused by this task and not fixed here. pixi-sandbox init --check, run with the canonical arguments from env-provisioning.md, reports one finding: .github/workflows/relock.yml no longer matches a fresh render. That file is untouched this session, its last change is the merge commit 7d8abb4, and it carries the same pixi-sandbox-version 0.5.2 stamp as the binary that renders it, so the drift predates this work and is not a version mismatch. It does not fail anything today: init --check appears in no pixi task, not in gates and not in ci.yml, so only the scheduled upgrade job in publish-sandbox.yml would catch it, and that job is the sanctioned route since it opens a pull request with the owned files. Reported for an owner decision rather than regenerated locally, because regenerating it is a change to a generated workflow that this task has no mandate for.

A first invocation of init --check without the explicit paths produced three findings including a missing launcher at the repository root. That was my error, not drift: env-provisioning.md already warns that the default launcher path is restore.sh at the root while this repository keeps it under scripts/. Only the canonical invocation above should be quoted.
<!-- SECTION:NOTES:END -->
