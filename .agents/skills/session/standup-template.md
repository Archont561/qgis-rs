# Session lifecycle templates

Four artifacts, one per phase, in the order a session produces them: the **opening prompt** that
starts it, the **standup** that proposes it, the **hand-off** that ends each task inside it, and
the **report** that closes it once the PR has merged. Fill them in literally — same headings, same
order. They are the shape a reviewer expects, and keeping them out of `SKILL.md` means editing a
template never touches the procedure.

The loop closes on itself: the report's last block **is** the next session's opening prompt. A
session that ends without writing one has handed the next session a reconstruction job.

## 1. Session opening prompt (written at close, pasted back at the next start)

```
Confirm the pixi environments and baseline the suite (expect 149 Rust tests across 30 integration
test files, 123 + 21 pytest, 44 bun — <the one or two environment facts that would otherwise waste
the first ten minutes: whether .pixi/envs is already materialized or needs scripts/restore.sh,
whether a publish-sandbox repack has landed on sandbox/developer-linux-64, whether gh and its
write scope are present, anything new that needs vendoring before the tree builds offline>).

Read `.knowledge/log.md` — <the dated heading> lists <K> open items — and `AGENTS.md` for the house
rules.

<Optional, when the session's first move depends on something only the remote knows: the one
command to run, and what each outcome means. "First, one look at the repo state: `git log
--oneline origin/main -3`. If <sha> is present, task-<n>'s last open path is proven by the merge —
read the run, check AC#<k>, complete the task file and close it. If it is not, leave the task In
Progress and say so.">

I want to take task-<n> this session — <one line on the shape, plus every decision already made,
spelled out, so the agent does not re-open settled ground>. In slices: <the locally provable ones>
first, <the ones needing a QGIS build, a push, a release or a native runner> last, which needs <the
sanction you are reserving>.

Propose the slice and stop. House rules are in `AGENTS.md` (D10: automation is an xtask subcommand,
not a shell script; D11: tests live in `tests/`, never in `src/`), the session procedure and its
templates are in `.agents/skills/session/`.
```

What makes this prompt work, and what makes it fail:

- **Name the expected test count.** It is the cheapest possible check that the environment produced
  the tree the last session left; a mismatch is the first thing worth saying out loud.
- **State the sanction boundary.** Which slices may be pushed, and which wait for a click. An agent
  that has to guess will either stall or push something you did not want pushed.
- **Carry the decisions forward, not the deliberation.** "Method A, already decided" saves a round
  trip; "we should decide between A and B" costs one.
- **Point at the log entry by date**, not at "the log" — the file grows, and the entry that matters
  is one of several.

## 2. Session standup (end of startup — then stop and wait)

```
Session proposal — <date>

Environment: <default + bun materialized | restored via scripts/restore.sh, ~4 min>; network
<github only | full>; baseline <N> Rust / <N> pytest / <N> bun passing, gates <green | red for
<the environmental reason>>.
Sandbox: <branch sandbox/developer-linux-64 current with main | behind — the last publish sandbox
run was <id>>.

Backlog: <N> To Do, <N> In Progress, <N> Done (36 / 3 / 8 as of 2026-10-03). Candidates, in
recommended order:
1. task-<n> (HIGH, <type>) — <one line: what it delivers and why now>
2. task-<m> …
   …
Not this session: task-<k> (blocked by task-<j>); task-<l> (deferred — <one-line reason>).

Slices: <the locally provable work> first; <anything needing a QGIS build, a push, a release or a
native runner> last, and only on your sanction.
Decisions I need before starting: <the ones that change the shape of the work, with a
recommendation each — or "none">.

Per task, "done" means: its acceptance criteria checked, one focused conventional commit,
pixi run gates green, task file completed in house format.
Need from you: confirm the scope (or pick differently) before I start.
```

## 3. Task hand-off (end of a task, before the commit)

```
task-<n> — <title>

Changed: <file> (<one line why>), …
Evidence: <the command that proves it> → <result>. Suite <N> Rust / <N> bun passing (was <N₀>/<N₀>).
Gates: fmt ✓ clippy ✓ clang-format ✓ taplo ✓ actionlint ✓ biome ✓ test ✓ convco ✓
Left undone: <anything an AC does not cover, or "nothing">.
```

## 4. Session report (after the PR merges)

```
Session report — <date>

Merged: PR #<N> "<squash title>" → main at <sha>.
Post-merge runs: ci <verdict, duration>, docs <verdict>, publish sandbox <verdict — or "not
path-triggered">, <any other triggered workflow> <verdict>.
Landed: <commit subject> (task-id), …

Tasks: task-<n> Done — every AC checked. task-<m> still In Progress — AC#<k> needs <the proof this
machine cannot produce: a QGIS build, a native runner, a cut release, a maintainer's click>.
Suite on merged main: <N> Rust / <N> bun passing (was <N₀>/<N₀>). Gates: green.

Recorded in .knowledge/log.md: <the headings appended this session>.
Open, in the order a session should consider them: <task id — one line on why it is next, or what
blocks it>, …
Environment facts for next time: <whether .pixi/envs was materialized or restored, what the
transport branch carries, what is not vendored yet, whether gh is still absent>.

Next session should start with:

> <template 1, filled in>
```

A session that produced ideas but no commits still writes a report — "Merged: nothing" is a result.
The ideas go to `.knowledge/log.md`, never into the file they speculate about, and the opening
prompt says what the next session should decide first.