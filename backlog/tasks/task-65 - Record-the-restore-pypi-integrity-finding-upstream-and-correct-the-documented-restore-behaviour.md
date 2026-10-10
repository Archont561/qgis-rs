---
id: TASK-65
title: >-
  Record the restore pypi integrity finding upstream and correct the documented
  restore behaviour
status: To Do
assignee: []
created_date: '2026-10-10 09:21'
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
