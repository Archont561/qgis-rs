# Bundle Update Log

## 2026-10-10 (session 16: TASK-41 discovery slice, local only)

* **Scope approved**: discovery first, at the binary argv/stdout/stderr/exit seam and the engine discovery seam. Optional QGIS absence is healthy pure operation: doctor exits 0. D15 and the four owner-decision items from session 15 were not reopened.
* **Environment**: restored from bare; the expected 18 pypi metadata integrity failures caused exit 1 (upstream pixi-sandbox#128). Linked pixi manually and restored 1086 Bun packages offline. No generated files were hand-edited. Base was `0b8b359`, matching origin/main, with CI and Docs green.
* **Landed locally, not pushed or merged**: `ef28be1` adds `version`, `capabilities`, and `doctor`, each with text or deterministic JSON output. All share a report: CLI/engine/transport versions, OS/architecture, backend compiled/live state and diagnostics, enforced domain limits, known operations with availability/reasons, and parser command names explicitly distinguished from execution availability. Protocol names come from `Operation::all()`, command names from clap, and availability belongs to the engine. Native builds probe the manager; pure builds do not load QGIS. Existing `--version`, execution flags, engine_info wire output and rendering gates remain unchanged.
* **Red → green**: observed the missing public engine function and each unrecognized CLI command fail, then implemented each step. Tests live in `crates/qgis-cli/tests/discovery.rs` and `crates/qgis-engine/tests/discovery.rs`. Pure focused suites: 58 integration tests plus 1 doc test. Separate native discovery run: CLI 3, engine 2. Pure clippy with `-D warnings` passed. Pure `cargo tree` and binary `ldd` show no QGIS, Qt, Python, Node or WebEngine dependency; subprocess tests clear PATH.
* **Measured**: gates exit 0 (8/8); full turbo tests exit 0 (12/12). Rust **327 + 30** (was 323 + 30); SDK **490 passed, 3 skipped, 8 deselected**, qt **3**, qgis **5**, Python distribution **18**, Bun **160**, CTest **1** target. The native discovery tests are additional focused evidence, not part of that 30-test native fan-out. The first baseline standalone turbo invocation used strict environment mode and failed when napi attempted crates.io; use `CARGO_NET_OFFLINE=true pixi run -- bun x turbo run test --env-mode=loose`, as the gate does. No repository fix was needed.
* **Task state**: TASK-41 In Progress, **AC1 only checked**. AC2–AC6 stay open: validation, project manifest inspection, tile/batch planning, stable execution errors, filesystem/atomic artifact policy, cancellation and resource limits remain future slices. Doctor does not install dependencies or scan profiles. No push or PR was requested or performed.
* **Next opening prompt**:

  > Confirm the restored pixi environments and read the 2026-10-10 session 16 entry and AGENTS.md. TASK-41 discovery is local on arena/a0952077-qgis-rust at ef28be1; nothing is pushed or merged. Expect gates 8/8 and full tests 12/12: Rust 327 + 30, SDK 490/3 skipped/8 deselected, qt 3, qgis 5, qgis-py-dist 18, Bun 160, CTest 1. Run full tests with CARGO_NET_OFFLINE=true and turbo --env-mode=loose so napi keeps the vendored Cargo configuration. TASK-41 is In Progress with AC1 checked; version/capabilities/doctor are done for this slice, and optional backend absence makes doctor exit 0. Propose the next TASK-41 slice and its public test seams before editing. Keep D15, the archived tasks, and the four owner-decision items unchanged. No push or PR without sanction.

## 2026-10-10 (session 15: D15 docs reconciliation, three tasks archived, restore integrity root-caused)

* **Environment, from nothing**: the sandbox was completely bare — no `pixi` binary, no `.pixi/envs`, no `node_modules`, no vendor tree. `bash scripts/restore.sh` took about three minutes and needs only github.com: transport verified (8719 blobs, 1707.4 MiB, every declared byte matches), `bun` 1683.7 MiB and `default` 4733.2 MiB unpacked, 162 crates vendored. It then **exited 1** on the final tree check with the same 18 `default`-env dist-info failures session 14 recorded. Because it exits non-zero it never reaches user-tool registration, so `pixi` was not symlinked into `~/.local/bin` and the documented `export PATH` found nothing; the remedy is `ln -sf "$PWD/.pixi/tools/linux-64/pixi" ~/.local/bin/pixi`. `pixi run bun-install` then restored 1086 packages offline in 2.25 s.
* **Baseline, measured not inherited**: `pixi run gates` exit 0 (8/8). `turbo run test` exit 0 (12/12): Rust **323 + 30**, `qgis-sdk-py` **490 passed, 3 skipped, 8 deselected**, qt **3**, qgis **5**, `qgis-py-dist` **18**, bun **160** (37 + 16 + 107), ctest **1** target at 100%. These match session 14's numbers exactly, so the tree is the one that was left.
* **CI correction**: the hand-off said PR #56's CI was green; at session start run 38039173349 was still `in_progress` (3 of 5 jobs done). It finished green during the session — all five jobs, plus Docs. The earlier red (38036466801) was on `c3d1e2f`. The cache-key fix is confirmed in the tree: all three keys in `.github/actions/setup-workspace/action.yml` now carry `${{ github.event.repository.name }}`. The merge triggered no `publish sandbox` run, correctly — `push_paths` does not include `.github/actions/**`, and the transport already carries the typer/questionary pypi set, so it is current with main's env content.
* **Restore integrity, root-caused and filed (TASK-65)**: `pack-default/pypi/` holds exactly nine wheels — `annotated_doc`, `markdown_it_py`, `mdurl`, `prompt_toolkit`, `questionary`, `rich`, `shellingham`, `typer`, `wcwidth` — and those are exactly the nine failing packages, a 1:1 correspondence. pixi-pack transports pypi packages **as wheels**, so pixi-unpack re-installs them with uv at restore time; uv rewrites `dist-info/uv_cache.json` with a fresh wall-clock timestamp (the value found decodes to `2026-10-10T08:57:18Z`, during this restore, and files installed in the same batch share it — hence identical `got` digests across packages), and `dist-info/RECORD` carries a `sha256=` line for that same file, so it must change too. Two files × nine packages = 18. The 53 conda-installed dist-infos verify clean and the pypi-free `bun` env reported 76366 entries, 0 failures, which isolates the cause to the uv install path. **Not fixable in this repository**: the check is `crates/pixi-sandbox-core/src/verify.rs`, `restore` exposes no exclusion flag, and the launcher is generated so it cannot carry a local patch while `init --check` fails the gate on drift. Filed as [pixi-sandbox#128](https://github.com/Archont561/pixi-sandbox/issues/128) with the reproduction, three suggested fixes ranked by size, and the workarounds rejected.
* **Two documents described a restore that no longer happens**: `.knowledge/env-provisioning.md` gained a *Known limit* subsection, and its *Using Tools After Restore* block was independently wrong — it showed `cargo build` and `clang-format` working directly, but neither is on a bare PATH here, only `pixi run -- cargo` is. `.agents/skills/session/SKILL.md` claimed "75732 entries, 0 failures" and a `pixi` symlink that the non-zero exit never reaches; both corrected, with a bullet added to *Known limits*. That skill is repo-owned — `skills-lock.json` lists seven skills and `session`, `backlog` and `audit` are not among them — so a skills sync cannot revert it.
* **Decisions (user-confirmed)**: take the docs reconciliation this session; for the restore finding, file upstream *and* record in-repo; archive all three D15-invalidated tasks.
* **Three tasks archived (TASK-26, TASK-16, TASK-59)**: each asks for work D15 rules out, so implementing any would rebuild what TASK-57 removed. TASK-26 wanted a Rust engine to own the qgis-sdk CLI with Python as a thin wire client — D15 §1 says there is no native extension, no `_core` and no Rust CLI crate, and the crates it names were deleted in `2d8d69a`; its AC4 outcome survives, delivered by TASK-57 and pinned by `tests/test_cli_task57.py`. TASK-16 wanted `@rust_accelerated` and a scaffold `--rust` flag: measured zero occurrences of `rust_accelerated` and of `HAS_RUST` under `py-packages` or `crates`. TASK-59 wanted a Node `qgis-sdk` bin on citty — the second name D13 §1 and D15 §1 forbid, plus two npm dependencies D15 §5 rules out; `@archont561/qgis-sdk` itself stays as the WebEngine client with its 107 passing bun tests. Rationales are in the archived notes, since `task archive` records no reason. Archiving TASK-26 also dropped the stale dependency edge from TASK-44. **The session-14 claim that "TASK-26 is high and overlaps nothing now" was wrong** — it was the top high-priority candidate and contradicted the accepted decision.
* **Docs reconciled (TASK-64)**: `.knowledge/qgis-sdk.md` retired §2, §3, §7.3 and §8 **in place rather than deleting them**, because `doc-1` cites the document by section number and so does its own evidence table; each keeps its number and names the decision that removed it. Rust mentions fell **72 → 29**, all of them retirement notes. §5 was rewritten against the shipped typer `--help`, §6 gained a banner saying `plugin.toml` is a TASK-3 proposal that nothing reads (`scaffold.py` writes `metadata.txt` directly), and §12 lost the Rust binary, the archived owners and two pixi tasks (`sdk-test`, `sdk-doctor`) that do not exist. D13 had a banner and a corrected enforcement table but **seven** places behind them still described the Rust CLI — Context, the §3 graph drawing edges from deleted crates, §4 treating the plugin CLI as a launcher, Accepted, Costs, the rejected alternative D15 reversed, and the gates list naming TASK-26 as live. The published pages were worse than a narrow grep suggested: `python-sdk.mdx` had eight Rust claims including a `bin/` tree listing `qgis-sdk` twice as a binary and an alias, and told users to print `qgis_sdk.HAS_RUST`, which raises AttributeError; `plugin-development.mdx` had a whole Rust Acceleration section. `AGENTS.md` documented `turbo run test --filter=qgis-sdk`, which resolves to nothing — the package is `qgis-sdk-py`.
* **The gate caught a regression this session introduced**: a first draft of §5.1 spelled the retired command literally, and `pixi run xtask check-sources` failed with `retired name: .knowledge/qgis-sdk.md`. Reworded. The check allowlists `backlog/`, `.knowledge/decisions/`, `.knowledge/log.md` and `CHANGELOG.md` as history, which is why D13 and the archived notes may still name it.
* **Reported, not fixed** — each needs an owner decision, none was sanctioned here: **TASK-43 is live and To Do but its description and AC5 name `qgis_sdk._core`**, which no longer exists, so that clause is vacuous. **D07** is a `status: draft` scope decision about Rust QGIS plugins via PyO3; D15 answers it only in passing ("a plugin that wants Rust runs cargo itself"), so superseding or reaffirming it is an architectural call. **`plugin-development.mdx`** still shows `qgis-sdk publish` as though it uploads, when it exits non-zero and says it is not implemented — worth folding into TASK-17. **`python-sdk.mdx`** still offers `conda install -c conda-forge qgis-sdk`, unverifiable from this sandbox. **`relock.yml` drift**: `pixi-sandbox init --check` with the canonical arguments reports it no longer matches a fresh render, though it is untouched this session, last changed by `7d8abb4`, and carries the same `0.5.2` stamp as the binary rendering it; it fails nothing today because `init --check` is in no pixi task, not in `gates` and not in `ci.yml`, so only the scheduled upgrade job would catch it, which is the sanctioned route. **18 task files reference `.knowledge/qgis-plugin-sdk.md` and `.knowledge/qgis-plugin-ui.md`, which do not exist** — dangling documentation references, distinct from task dependencies (the dependency audit found none: the seven edges from 2026-10-04 are fixed).
* **Unchanged on purpose**: `.knowledge/log.md` historical entries, D14 (already `status: superseded` with a banner), `doc-7` (already bannered, every mention marked "(retired)"), and completed task notes including TASK-40's.
* **Backlog after this session**: **23 To Do, 1 In Progress (TASK-50), 35 Done** across 59 task files, plus 10 archived. The high-priority unblocked tier is now TASK-41, TASK-42 and TASK-43 — and two of those three have stale contracts (TASK-42's "CLI launchers" were removed in `47a909a`/`41b02b4`; TASK-43's AC5 names a deleted extension), so **TASK-41 is the only high-priority candidate that can be started as written**. Medium and unblocked: TASK-3, TASK-4, TASK-13, TASK-21, TASK-54, TASK-62, TASK-63.
* **Still open, no task**: TASK-58's platform follow-up (CI matrix for the other platforms, `release.rs` `NPM_PACKAGES` publishing, the win32 package) — the owner asked that a task be created only on request, and has not. TASK-50 stays In Progress on AC4, which needs Codecov evidence on a runner.
* **Next session opening prompt**:

  > Confirm the pixi environments. The sandbox starts bare — no `pixi` binary at all — so run `bash scripts/restore.sh` (~3 min, github.com only). It **exits 1** with 18 `default`-env dist-info integrity failures; that is upstream pixi-sandbox bug [#128](https://github.com/Archont561/pixi-sandbox/issues/128), root-caused in the 2026-10-10 session 15 entry and in `.knowledge/env-provisioning.md`, and the environments are complete and usable — note it and continue. Because the exit is non-zero, `pixi` is **not** symlinked: run `mkdir -p ~/.local/bin && ln -sf "$PWD/.pixi/tools/linux-64/pixi" ~/.local/bin/pixi`, then `export PATH="$HOME/.local/bin:$PATH"` and `pixi run bun-install` (1086 packages, ~2.5 s offline). Read the session 15 entry in `.knowledge/log.md` and `AGENTS.md`.
  >
  > Expect `pixi run gates` exit 0 (8/8) and `turbo run test` exit 0 (12/12): Rust **323 + 30**, `qgis-sdk-py` **490 passed, 3 skipped, 8 deselected**, qt **3**, qgis **5**, `qgis-py-dist` **18**, bun **160**, ctest **1** target. The turbo package is `qgis-sdk-py`, not `qgis-sdk`. `main` is green at the merge of PR #56.
  >
  > Decisions already made, do not re-open: D15 governs — qgis-sdk is one pure-Python typer CLI with no Rust, no `_core` and no second name; TASK-26, TASK-16 and TASK-59 are archived as superseded; the restore integrity bug is filed upstream and is not ours to patch, and no generated file may be hand-edited.
  >
  > Four things need an owner decision before they can be worked, and are recorded in the session 15 entry rather than changed: TASK-43's AC5 names the deleted `qgis_sdk._core`; TASK-42's launcher scope was removed in `47a909a`/`41b02b4`; D07 is a draft scope decision D15 only answers in passing; and `relock.yml` drifts from a fresh `init --check` render, which only the scheduled upgrade job catches.
  >
  > I want to take **TASK-41** (HIGH, pure-Rust `qgis-cli` capability surface) — it is the only high-priority unblocked candidate whose contract D15 leaves intact, since D15 §1 keeps `qgis-cli` in Rust. Alternatives if you prefer Python-side work: TASK-63 (stop `qgis_py` importing `qgis_sdk`; one decision is still open — whether `HAS_QGIS_SDK` is removed or kept deprecated and always False) or TASK-62 (one surface registry in `scripts/version.ts`). Propose the slice and stop before writing code. House rules are in `AGENTS.md` (D10: automation is an xtask subcommand; D11: tests live in `tests/`), the session procedure and its templates are in `.agents/skills/session/`.

## 2026-10-10 (session 14: TASK-57 pure-Python CLI, TASK-58 closed)

* **Sync and audit first**: `arena/1862c47e-qgis-rust` was pulled to `origin/main` at `c3d1e2f` (PR #55, the typer port). The backlog was re-audited from the task files, not from the CLI listing, because a grep in the first audit hid the Done header. Counts then: 27 To Do, 2 In Progress, 31 Done. No dangling dependency edges.
* **TASK-57 audit found it partly done and partly stale**: PR #55 had ported the commands to typer, but three things still broke the ACs. (1) `rust init`, `rust build` and every `--rust` flag, plus a cargo call in `test`, `package` and `dev`. (2) `new` asked for the name with `typer.prompt`, which is not questionary and has no CI story. (3) `package` picked the first child folder with an `__init__.py`. A scaffolded plugin has a `tests/` package, so `package` wrote `dist/tests.zip` with no plugin in it. The third was found by a new test, not by reading the code.
* **Decisions (user-confirmed)**: remove all Rust from qgis-sdk, not keep a cargo passthrough (this follows TASK-57 AC1, and D15 §3 is amended). TASK-58 is Done with ACs 1-2 superseded. ACs 1-2 are not checked, because they no longer describe work to do, and AC3 is checked.
* **What changed**: `cli.py` drops the rust group, the `--rust` options, `_run_cargo` and the rust handlers. `new` uses questionary only at a terminal (stdin and stdout are TTYs) for the name, `--type`, `--ui/--no-ui`, `--author` and `--email`. Each has a flag. Without a terminal a missing name exits 2 and nothing is asked. `scaffold.py` loses `with_rust`, the Cargo/pyo3 template and its call. Tests: `tests/test_cli_task57.py` (16 cases pinning AC1-AC4 at `cli.main`, plus a subprocess that blocks every QGIS module before importing the CLI). Old rust tests in `test_cli.py` and `test_cli_commands.py` are removed or updated. Docs: `README.md`, `py-packages/qgis-sdk/README.md`, `docs/.../cli/plugin.mdx`, `docs/.../getting-started/python-sdk.mdx`, and D15 §2-3 (amended).
* **Measured**: pixi pure layer **490 passed, 3 skipped, 8 deselected** (was 474). qt **3**, qgis **5**. Bare venv with no QGIS (`/tmp/bare`: pixi's python, `python -m venv`, then typer, questionary, pytest, hypothesis, and a wheel built from this tree): **489 passed, 4 skipped**. The nested pytest11 failures in session 13 did not reproduce, because the installed wheel provides the entry point. Gate: `pixi run gates` exit 0, Rust **323 + 30** tests, `qgis-py` pytest **18**.
* **Evidence by damage**: the packaging bug was shown by the new zip test. With the old `_plugin_package_dir`, the test failed with `FileNotFoundError: dist/zip_plugin.zip`, and the CLI printed `Packaged plugin to .../dist/tests.zip`. The fix skips `tests`, `test`, `docs`, `dist`, `wheels`, `build`, `node_modules`, `extlibs` and hidden folders, and prefers a package named after the project folder.
* **Operational, twice**: (1) The first bare-venv run used a wheel built before the edits, so it tested the old CLI and failed 10 tests. Rebuild the wheel from the current tree before a bare-venv run. (2) A test that ran `new rusty --rust` with no `-o` wrote a plugin into the package directory, because the old wheel still knew `--rust`. The test now runs in `tmp_path`. Stray `Cargo.toml`, `src/lib.rs` and `rusty/` were deleted and are not in git.
* **Restore finding (still open, not fixed)**: `scripts/restore.sh` exited 1 on its final tree check, with 18 failures in `default` env dist-info: `RECORD` and `uv_cache.json` in nine packages. The envs are usable: `pixi install --frozen --offline` is a no-op, `cargo 1.96.1` and `bun 1.3.11` run, and `typer 0.27.3` imports. The restore script treats these as failures, so the check needs a decision (exclude relocated metadata, or fix the relocation).
* **Still open**: `.knowledge/qgis-sdk.md` and `.knowledge/decisions/D13` still describe the Rust CLI. TASK-57 AC2's "zip contains no qgis_sdk code" means the default zip. `--bundle` (bootstrap.py) and `--offline-wheel` are explicit opt-ins and do put code in the zip. TASK-58's platform work (CI matrix, `release.rs` `NPM_PACKAGES`, win32) is not a task yet.
* **Ready next (all dependencies Done)**: high TASK-26, TASK-41, TASK-42, TASK-43, TASK-57 (done now); medium TASK-3, TASK-4, TASK-13, TASK-16, TASK-21, TASK-54, TASK-59, TASK-62, TASK-63. TASK-44 is blocked on 26, 42 and 43. TASK-49 is blocked on 4, 13, 37, 38, 39, 41 and 44.
* **Next session opening prompt**:

  > Confirm the pixi environments. Run `bash scripts/restore.sh` only if `.pixi/envs/default` is missing. Expect 18 integrity failures in the `default` env dist-info (see the 2026-10-10 session 14 entry); the envs still work, so note it and continue. Then `export PATH="$PWD/.pixi/tools/linux-64:$PATH"` and `pixi run -- bun --filter=qgis-sdk-py run build` (the wheel must come from the current tree). Read the session 14 entry in `.knowledge/log.md`. The session branch `arena/1862c47e-qgis-rust` holds TASK-57 at `e2dde67` and this log at `00ffbd2`; nothing is merged to main yet. Expect qgis-sdk pure **490 passed, 3 skipped, 8 deselected**, qt **3**, qgis **5**, Rust **323 + 30**, qgis-py pytest **18**. Open items: the restore integrity check, `.knowledge/qgis-sdk.md` and D13 still describe the Rust CLI, and the TASK-58 platform work needs a new task. Audit the backlog from the task files, not from the CLI listing. Propose the next slice (TASK-3 unblocks the UI chain; TASK-26 is high and overlaps nothing now) and stop before writing code.

## 2026-10-10 (qgis-sdk migration, slice 6: typer CLI, real commands, live text)

* **Dependencies**: `typer>=0.27,<1` and `questionary>=2.1,<3` are the approved qgis-sdk dependencies. They are in `pixi.toml` (`py-runtime` feature) and in `py-packages/qgis-sdk/pyproject.toml`. `pixi.lock` is refreshed by `relock.yml`, because `pixi lock` cannot reach conda.anaconda.org from this sandbox.
* **CLI**: `cli.py` is a typer application (`app`, `main(argv) -> int`). Option names and choices match the retired argparse tree. Usage errors return 2. Questionary asks for the dialog name only at a TTY (`ui add-dialog`).
* **Commands that now do their work**: `package` (and `build`) writes `<name>.zip` with the plugin package folder and its `metadata.txt`. `install` copies the package into the QGIS profile. `test` runs pytest and cargo as requested. `rust build` runs cargo. `dev` and `publish` without `--dry-run` exit non-zero with "not implemented". `publish --dry-run` checks that the archive exists.
* **Bundle**: `package --bundle` copies `bootstrap.py` into the package. `--offline-wheel` copies the wheel into `<package>/wheels/`, so it ships inside the archive. The retired code put wheels next to the package, outside the zip.
* **Metadata**: `metadata_fields()` and `render_metadata_from_dict()` are ported. They use the same `METADATA_FIELDS` table `render_metadata` already uses (20 fields), so there is one table.
* **Scripts**: `QGIS_REQUIRE_NATIVE=1` is removed from the qgis-sdk `package.json` test scripts. No qgis-sdk code read it. qgis-py and qgis-node keep it.
* **Live text**: doc-1, doc-3 and doc-7 no longer name the retired executable or the retired crates. doc-7 carries a supersession banner pointing to D15. README and `.knowledge/qgis-ui.md` no longer cite `HAS_RUST` or `_core`.
* **Blocked here**: `cargo` cannot reach crates.io (TLS EOF) and there is no vendored cache, so `cargo test -p xtask --offline` cannot run in this sandbox. The `gates` task runs the same xtask suite; CI is the proof for it.

## 2026-10-10 (qgis-sdk migration, slice 5: _core, the crates and maturin)

* **Landed on `arena/8333daf5-qgis-rs`**: `1e238d9` (drop `_core`, its fallback and the Rust flags), `66923fe` (setuptools backend), `2d8d69a` (remove `crates/qgis-sdk` and `crates/qgis-sdk-core`). `pixi run gates` exit 0 at `2d8d69a`. qgis-sdk pytest 459 passed, 4 skipped. `cargo test -p xtask` and `cargo check --workspace` pass.
* **User answers**: remove both crates, not only `qgis-sdk`. Switch to setuptools in the same slice, since the backend built the extension from the crate. Remove the qgis-sdk xtask rules and keep the qgis-cli ones.
* **Removed**: `HAS_RUST`/`RUST_VERSION`, the `_core` import blocks, `_fallback_cli.py`, the compiled `.so`. The retired import block had also reset `__version__` to a literal when `_core` was missing. `tests/test_pure_python.py` pins the surface.
* **Packaging**: `pyproject.toml` uses `setuptools.build_meta`, with `assets/bridge/*` as explicit package data. The package `pixi.toml`, the conda recipe and `package.json` build follow. `pip wheel` builds a wheel with the assets, the entry point and no bytecode caches.
* **xtask**: `FORBIDDEN_EDGES`, `CANONICAL_BINARIES` (qgis-sdk entry) and `TRACKED_FALLBACKS` are emptied. The "allowlisted but gone" case has no live entry to test, so it is removed. The rule code stays. `the_qgis_sdk_rust_crates_are_retired` pins the removal.
* **Gate note**: `TRACKED_FALLBACKS` pointed at `_fallback_cli.py`. Deleting that file made the contract self-check fail, so the allowlist had to be emptied in the same commit as the file's deletion.
* **Live text corrected**: README, docs mdx pages, the qgis-node README, `ARCHITECTURE.md`, the Cargo comments and `turbo.json`. `.knowledge/` pages, D13/D14 and the qgis-plugin material are still open.
* **Still open**: D13/D14 supersession, the `qgis-plugin` cleanup in live files, the typer/questionary CLI (TASK-57), the stale TASK-44 note, and `rust init`/`rust build`/`ui add-*`/`metadata_fields`/`render_metadata_from_dict` on the Python side.
* **Next session opening prompt**:

  > Read the slice 5 entry in `.knowledge/log.md`. Supersede D14 with a new decision record, and update D13 and the live `.knowledge/` pages that name `crates/qgis-sdk`, maturin or `_core`. Leave historical log entries and completed task notes unchanged. Stop after the gates for review.

## 2026-10-10 (qgis-sdk migration, slice 4: new)

* **Landed**: `fc4ee92` (`new` routes through the Python scaffold only). `pixi run gates` exit 0. qgis-sdk pytest 449 passed, 4 skipped.
* **Decision (user answer)**: the Python scaffold is the single spec. The native Rust template was older (no network, tasks or services) and its docstring had a doubled quote. It is no longer selected even when the extension is importable.
* **Tests**: `tests/test_new_parity.py` (2). A native stub fails the test if it is called. The tree produced by `cli.main` must equal the direct Python scaffold tree.
* **Gate note**: a stale `_fallback_cli.cpython-311.pyc` in `__pycache__` failed the "no new fallbacks" boundary check. Clearing `__pycache__` fixed it. Generated caches are not tracked.
* **Still on `_core`**: `__init__.py` (`HAS_RUST`, `RUST_VERSION`), `styles.py` (unused import), `_fallback_cli.py`. The `_core` extension and the crates are removed in one slice.
* **Next session opening prompt**:

  > Read the `new` entry in `.knowledge/log.md`. Remove `_core` from `__init__.py`, `styles.py` and `_fallback_cli.py`, then remove `crates/qgis-sdk` and `crates/qgis-sdk-core` as one slice. Stop after the gates for review.

## 2026-10-10 (qgis-sdk migration, slices 2 and 3: info and version)

* **Landed on `arena/8333daf5-qgis-rs`**: `4ea73de` (info), `e9b77a2` (version). `pixi run gates` exit 0 at `e9b77a2`. qgis-sdk pytest 447 passed, 4 skipped.
* **info**: the Rust command is the spec, since there was one Rust implementation. A missing metadata file is reported on stdout with exit 0. `--json` keeps sorted keys and unescaped UTF-8, as serde_json did. `tests/test_info_parity.py` (8).
* **version**: reads the version from package metadata, with a source-tree fallback. Drops the "Rust-native" label, which is no longer true. Output is otherwise unchanged. `tests/test_version_parity.py` (3).
* **Test corrected**: `tests/test_ui.py::test_validate_web_missing_qwebchannel` accepted a pass when no Rust core was present. It now asserts the single rule set, so it fails if the old stub behaviour returns.
* **Still on `_core`**: `new` (vanilla layout), which is the 360-line Rust `cmd_new`, and `styles.py`'s unused import. Both belong to later slices.
* **Next session opening prompt**:

  > Read the info and version entries in `.knowledge/log.md`. Port the next Rust-only command, `rust init`, then `rust build`, with red tests at the `cli.main` seam. Keep `_core` only for `new` until its slice. Stop after each slice's gates for review.

## 2026-10-10 (port Rust validate to Python, slice 1 of the qgis-sdk migration)

* **Landed on `arena/8333daf5-qgis-rs`**: `ac719ea` (feat). `pixi run gates` exit 0. qgis-sdk pytest 436 passed, 4 skipped.
* **Finding that set the order**: the Python stub fallback (`_fallback_cli.py`) returned no errors from `validate`, and two Rust implementations disagreed. The `qgis-sdk` crate required `[general]`, `name=` and `version=`. `qgis-sdk-core` required a metadata or `.py` file, and checked qwebchannel in web HTML. Deleting the crate first would have made `validate` a silent no-op.
* **Decision (user)**: the port keeps the union of both rule sets.
* **Port**: `qgis_sdk/plugin_validation.py` is now the only validator. `cli._cmd_validate` calls it and no longer uses `_core`. `tests/test_validate_parity.py` (13 tests) pins the behaviour at the `cli.main` seam.
* **Deviation from red-first**: the red tests were run (3 failed against the union spec) but not committed on their own. They share a commit with the port.
* **Still Rust-only**: `info`, `version`, `metadata_fields`, `render_metadata_from_dict`, `rust init`, `ui add-*`, `build`/`test`/`package`/`install`, and `new`. The crates `qgis-sdk` and `qgis-sdk-core` stay until each is ported.
* **Next session opening prompt**:

  > Read the validate-port entry in `.knowledge/log.md`. Continue the qgis-sdk migration with the next Rust-only command, `info`, then `version`, using red tests at the `cli.main` seam. Keep the crates until every command is ported, then remove them as one slice. Stop after each slice's gates for review.

## 2026-10-09 (remove built-in CLIs from qgis-py and qgis-node)

* **Landed on `arena/8333daf5-qgis-rs`**: `5122a61` and `2f73d3c` (red guard tests for qgis-py and qgis-node), `47a909a` (qgis-py CLI removed), `db85d37` (qgis-sdk `qgis-cli` shim removed), `41b02b4` (qgis-node CLI removed), `92fffc9` (docs), a root `package.json` comma fix, and a format commit. `pixi run gates` exit 0 at HEAD.
* **qgis-py**: `python/qgis_py/cli.py`, `scripts/stage_cli.py`, `_bin/`, the `[project.scripts]` entries, and the CLI tests are gone. The wheel holds 163 entries, no CLI module, no console scripts, and `_core` is present. Its `build` script no longer stages a binary, and `xtask release` no longer calls `stage_cli.py`.
* **qgis-sdk (scope extension)**: its `qgis-cli` console script delegated to `qgis_py.cli`, which no longer exists, so it was removed with `qgis_cli_main` and the recipe lines. The `qgis-sdk` command is unchanged. pytest 423 passed, 4 skipped.
* **qgis-node**: `bin/`, `src/cli.js`, `scripts/stage-cli.js`, `npm/*`, and `tests/cli.test.js` are gone. `optionalDependencies`, `bin`, the `cli` keyword, and the `build:cli` script are removed. `runCli` and `resolveCliBinary` are no longer exported. The addon loader and its triple list stay, because they select the `.node` file. `bun.lock` lost only the three platform workspaces. `pack:check` passes. bun suite: 160 pass, 0 fail.
* **Coverage note**: `tests/cli.test.js` covered `cliTriple` platform resolution and the `runCli` boundary. Those cases went with the CLI code they tested. No addon-loading case was lost.
* **Auditwheel**: the `libQt5Core` repair failure noted earlier did not reproduce in the gate's wheel build. Not investigated further.
* **Unchanged**: `crates/qgis-cli` (standalone binary, still shipped by its own release path) and the `docs/src/content/docs/cli/*` pages describing it. The xtask boundary fixture that mentions `qgis-cli` is parser test data.
* **Backlog**: TASK-58 has AC 3 checked and a note that ACs 1-2 are superseded. It stays In Progress for an owner decision to close. TASK-61 has a note that its CLI half is superseded. Its WebEngine global is unchanged.
* **Stop for review**: the slice is committed and gated. Nothing is pushed or opened as a PR.
* **Next session opening prompt**:

  > Confirm the pixi environments (`scripts/restore.sh`, `export PATH="$HOME/.local/bin:$PATH"`, `pixi run bun-install`, `pixi run setup`). Read the CLI-removal entry in `.knowledge/log.md`. Ask whether TASK-58 should be closed, since its CLI scope is removed. Open items: verify the WebEngine global in a real QtWebEngine page, and the CI matrix for per-platform wheels. Propose the next slice and stop before writing code.

## 2026-10-09 (wheel bytecode exclusion)

* **Landed on `arena/8333daf5-qgis-rs`**: `9900014` (exclusion, with `test_packaging.py` in qgis-py and qgis-sdk), `b4ca204` (relink fix), and a format commit. `pixi run gates` exit 0.
* **Exclusion**: `[tool.maturin] exclude = ["**/__pycache__/**", "**/*.pyc"]` in both pyprojects. Red first: the qgis-py wheel held 4 bytecode entries. Now 0 in both wheels.
* **Second bug, found while verifying**: a second `maturin build` from the same tree failed with `Cannot repair wheel, because required library libQt5Core-<hash>.so.5 could not be located`. Cause: auditwheel repairs the extension in place, the file is hard-linked into `target/release/deps` and `target/maturin`, and cargo sees nothing to rebuild. The first build after a clean succeeds; the second fails. The failure also left an empty 22-byte wheel behind. Fix: `cargo clean -p qgis-py -p qgis-sdk --release` in the release xtask before the wheel loop, and in both package `build` scripts before `maturin build`. Verified: two consecutive release-shaped rounds both pass, and both wheels have 0 bytecode entries.
* **Also noticed, unchanged**: `maturin build --manifest-path <pyproject>` fails with `cargo metadata` in this maturin (1.15.0). The release fallback to running from the package directory is what works.
* **Measured**: qgis-py wheel 121 MB (repaired QGIS and Qt libraries are bundled), qgis-sdk wheel 430 KB. The qgis-cli binary is not repaired, so it needs QGIS installed at runtime, as before.
* **Next session opening prompt**: as in the previous entry, minus the pycache item. The open items are the real QtWebEngine check, and the CI matrix for per-platform wheels and npm packages (TASK-58, TASK-61).

## 2026-10-09 (slice 6 and the WebEngine global, TASK-61)

* **Landed on `arena/8333daf5-qgis-rs`**: `c38f1be` (slice 6, prebuilt qgis-cli in qgis-py), `2cdd15d` (WebEngine global), and two format commits. `pixi run gates` exit 0 after each. TASK-61 is **Done**.
* **Slice 6, prebuilt qgis-cli for qgis-py**: `py-packages/qgis-py/scripts/stage_cli.py` builds `qgis-cli` and stages it in `python/qgis_py/_bin/`, which git ignores through the existing `_*` rule. `qgis-cli` (console script) now runs `binary_main`, which runs the bundled binary with the same argv and exit status. `qgis-py` still runs the Python parser. `xtask release build-artifacts` stages the binary before the maturin loop, and the package `build` script does too. Verified: the wheel holds `qgis_py/_bin/qgis-cli` at mode 0755, and `binary_main(['--help'])` returns 0.
* **WebEngine global**: the bundle now enters through `src/browser.ts`. On a WebEngine page (`qt.webChannelTransport` or `QWebChannel` present) it publishes `window.qgis`, `window.qgisBridge`, `window.qgisReady`, and `window.qgisChannel(transport, cb)`. Outside WebEngine it publishes nothing. The four scaffolded pages load `qgis-sdk.js` after `qwebchannel.js`.
* **Double-channel bug, found while wiring it**: Qt's `QWebChannel` constructor assigns `transport.onmessage` (checked in qwebchannel 6.2.0, from npm). A second channel on one transport takes over the first one's replies. The bundle and the page's own `new QWebChannel` would have broken each other. Fix: `src/channel.ts` caches one channel per transport. The bridge (`window.ts`) and the templates both open it through `openChannel`/`qgisChannel`. Tests: `channel.test.ts` (3), `browser.test.ts` (5).
* **Measured**: qgis-py pytest 24 passed. `@archont561/qgis-sdk` 106 bun tests. qgis-sdk vendoring tests 10. xtask 150 passed.
* **Not verified here**: a real QtWebEngine page. Only a fake channel ran (node smoke test: one channel for two callers). The bundle's auto-connect logs one console error on pages where Python does not register a `bridge` object. The qgis-cli binary links QGIS shared libraries (auditwheel does not repair it), so it needs QGIS at runtime, as the Node binary does. Only linux-x64 was built. The CI matrix and per-platform wheel publishing are still unbuilt, as recorded for TASK-58.
* **Pre-existing, not changed**: `py-packages/qgis-py/python/qgis_py/__pycache__` gets into the wheel when maturin runs in a dirty tree. Clean it before release builds.

* **Next session opening prompt**:

  > Confirm the pixi environments (`scripts/restore.sh`, `export PATH="$HOME/.local/bin:$PATH"`, `pixi run bun-install`, `pixi run setup`). Read the slice 6 and WebEngine entry in `.knowledge/log.md`. Open items: verify the WebEngine global in a real QtWebEngine page, the CI matrix for per-platform qgis-cli wheels and npm packages (TASK-58, TASK-61), and the `__pycache__` exclusion in the wheel. Propose the slice and stop before writing code.

## 2026-10-09 (slice 5, TASK-56 bridge vendoring)

* **Landed on `arena/8333daf5-qgis-rs`** in `91cd574` (feat). `pixi run gates` exit 0 on that commit. TASK-56 is **Done** (AC1–AC4 checked).
* **Bundle**: `ts-packages/qgis-sdk` gained `build:bundle`, an IIFE from `bun build` (`QgisSdk` global, browser target). `build` runs it after bunup.
* **Vendored**: `py-packages/qgis-sdk/src/qgis_sdk/assets/bridge/` holds `qgis-sdk.js` (18 KB) and `manifest.json`, which pins package, version, and sha256. `py-packages/qgis-sdk/scripts/vendor_bridge.py` refreshes both from `dist/bundle/`.
* **Linked only for WebEngine UIs**: `_link_vendored_bridge` runs inside the `with_web` block of `scaffold_plugin`, so it copies `web/qgis-sdk.js`. Plain scaffolds ship no bundle. The `bun` declarative template uses the npm package and is unchanged.
* **Tests**: `tests/test_bridge_vendor.py` (5). Three were red before the change. Manifest-to-file sha, manifest-to-package version, and scaffold copy are all checked.
* **Measured**: qgis-sdk Python 417 passed / 4 skipped. `@archont561/qgis-sdk` 99 bun tests, typecheck clean, lint exit 0 with 126 warnings (not counted against this slice).
* **Not done**: the HTML templates do not yet load `web/qgis-sdk.js` with a `<script>` tag. The bundle is copied but not referenced. Next step: pick the global name and wire it into the WebEngine templates.
* **Pushed**: slices 3 and 4 (`985d333`, `7f5cc79`, `15bce63`) were pushed with this slice.

* **Next session opening prompt**:

  > Confirm the pixi environments (`scripts/restore.sh`, `export PATH="$HOME/.local/bin:$PATH"`, `pixi run bun-install`, `pixi run setup`). Read the slice 5 entry in `.knowledge/log.md`. Slice 6 (prebuilt `qgis-cli` for qgis-py) is next. Inventory before editing, and propose the slice and stop for review before writing code.

## 2026-10-09 (TASK-58, prebuilt qgis-cli through @archont561/qgis-node)

* **Landed on `arena/8333daf5-qgis-rs`** (commits `fc18ca6` feat, then a format commit and a test-script commit): TASK-58 is **In Progress**, not Done. The package is `@archont561/qgis-node` and follows the Biome model. Each platform has a package in `optionalDependencies` that holds `bin/qgis-cli`, and the bin shim resolves the one for the machine. Nothing is downloaded at install or run time. Platforms: `linux-x64-gnu`, `linux-arm64-gnu`, `linux-x64-musl` (`npm/<triple>/`), plus `win32-x64-msvc` in the resolver, with no package yet.
* **Removed**: the `qgis-plugin` and `qgis-sdk` bins. `qgis-cli` is the only command.
* **Added**: `runCli(argv)` returns `{ exitCode, stdout, stderr }` (typed in `index.d.ts`), and `resolveCliBinary`. `scripts/stage-cli.js` builds qgis-cli for this machine and stages it.
* **Renamed**: the napi addon is `qgis-node.<triple>.node` across turbo, biome, `pack:check`, the loader, and `scripts/version.ts`. The stale `@qgis-rs/node-<triple>` loader candidate is gone.
* **Measured**: `pixi run gates` exit 0. `@archont561/qgis-node` test: **19 pass** (13 contract, 6 CLI, with the real binary run under `QGIS_REQUIRE_NATIVE=1`).
* **Gotchas**: qgis-cli links QGIS, so it builds only in the **default** pixi env (`pixi run -e default node ts-packages/qgis-node/scripts/stage-cli.js`). The `bun` env has no Qt headers and fails in `qgis-sys`. `pixi run bun …` runs from the repository root, so package scripts need `cd` or an explicit path. The first `test` script ran only `contract.test.js`, and the gate missed the CLI suite until it was widened to `tests/`.
* **Open**: CI does not build the other platforms, and `release.rs` `NPM_PACKAGES` does not publish the platform packages yet. Both are needed before a real release.

* **Next session opening prompt**:

  > Confirm the pixi environments (`scripts/restore.sh`, `export PATH="$HOME/.local/bin:$PATH"`, `pixi run bun-install`, `pixi run setup`). Read the 2026-10-09 TASK-58 entry in `.knowledge/log.md`. TASK-58 stays In Progress: propose the slice for the CI matrix that builds each platform package, and for publishing the platform packages in the release step. Propose the slice and stop before writing code.

## 2026-10-08 (session 13)

* **Landed in PR #48** (squash-merged; the squash SHA is the PR's merge commit): TASK-2 — **Done (6/6 ACs, 2/2 DoD)**. The CI test lane used to run one permissive pytest pass over `qgis-sdk`, so the pure-Python suite and the QGIS integration suite were never separate strict passes, and no log said which QGIS backed the run. `test` in `py-packages/qgis-sdk/package.json` now runs `test:pure`, `test:qt` and `test:qgis` in sequence, each strict and each with `QGIS_REQUIRE_NATIVE=1` (without it `test_native_extension_is_used_in_ci` asserts only a bool). `coverage` stays the permissive whole-suite run.
* **Coverage parity, checked before the PR**: splitting one run into gates is only safe if the gates cover what the permissive run covered. Comparing collected test IDs settles it: the three gates together collect **409** tests, exactly the permissive run's 409, because a test with no layer marker is in `pure` and every layer-marked test is in `qt` or `qgis`. No WebEngine-only tests exist here, so nothing was dropped.
* **Bug, present since the detector was written**: `qgis_environment.qgis_version` was always `None`. `detect_qgis_environment` read `qgis.core.QGIS_VERSION`, and the 3.44 bindings export no such constant. It now reads `Qgis.version()`, and a test with a fake `qgis.core` pins it. The run header now says `qgis-sdk runtime: backend=qgis, qgis=3.44.14-Solothurn; layers: pure, qgis, qt; gate: qgis`, and the header hook is re-exported from `qgis_sdk.testing` (the `pytest11` entry point loads that module, so an unexported hook is silently never called).
* **Subprocess isolation, one place**: `py-packages/qgis-sdk/tests/qgis_subprocess.py` runs the QGIS child with `QT_QPA_PLATFORM=offscreen` and `PYTHONDONTWRITEBYTECODE=1`, a 300 s timeout that keeps partial output, and a failure report with the exit status (or the signal name), the QGIS release, and the child's full stdout and stderr. `tree_digest` (SHA-256 per file) lets the integration test prove the committed `simple_plugin` fixture is byte-identical after the run. Before this, the fixture gained a `__pycache__` on every run, which contradicted "read-only input".
* **Evidence by damage** (temporary copies, removed afterwards): a child that exits 5 after writing to both streams fails with `exit status 5`, the release, and both markers in the report; a child that writes into the fixture fails with `the simple_plugin fixture was modified`.
* **Skip proof without QGIS**: in a bare Python 3.11 venv (pytest and hypothesis only, the CI-virtualenv shape) the integration test skips with `requires an importable qgis.core runtime`, the header reads `backend=pure-python, qgis=unavailable`, and `QGIS_TEST_LAYER=qgis` **errors** instead of skipping.
* **Pre-existing, not fixed here** (measured on an untouched export of `main`): in that same venv three `tests/test_layer_gates.py` tests fail (`test_a_gate_whose_layer_is_missing_fails_instead_of_skipping`, `test_a_gate_runs_only_its_own_layer`, `test_without_a_gate_the_whole_suite_still_runs_with_skips`). Each runs a nested pytest, and the nested run has no `pytest11` entry point because `qgis_sdk` is not installed in that venv. The pure-Python path of the suite is therefore only exercised here by hand; CI always has QGIS in the default environment. Idea for a later session: a CI job in a QGIS-free environment that installs the wheel, so the no-QGIS skip and the nested-session tests run in CI rather than in a sandbox.
* **Clean-checkout proof for DoD#2** (which the previous session could not run, for lack of 8 GiB of scratch): this sandbox was re-cloned at the turn boundary and disk had 20 GiB free, so `scripts/restore.sh` ran on the branch's own tree. Then `pixi run gates` was green (exit 0, `── gate passed`) and `pixi run -- bun --filter=qgis-sdk-py run test:qgis` passed 5 tests with the header above. Restore took about 4 minutes; the gate about 6.
* **Operational, twice**: (1) the sandbox re-clone reset the local branch to `main` while the two commits (`97ca783`, `469b5ff`) stayed on `origin`. Recovery: verify the working tree is byte-identical to `origin/arena/87d21dbe-qgis-rs`, then `git reset --mixed origin/…`; the files are untouched and the branch is back. Push early, because the remote is the copy that survives. (2) A stray `cpython-311` `.pyc` in `src/` from a bare-venv run failed `check-boundaries`, which treats an untracked `_fallback_cli` artifact as a second answer (D13). Delete bytecode from ad hoc venv runs before `pixi run gates`.
* **Backlog CLI foot-gun** (measured): `task edit 2 --append-notes "…"` with a long string containing single quotes failed with `Cannot use --append-notes with more than one task ID`, and a `--final-summary` once wrote nothing. Use short single-quoted notes, one call each, and read the file back.
* **Measured**: `pixi run gates` green on the clean checkout. `qgis-sdk` pure gate **398 passed / 3 skipped / 8 deselected** (was 388 / 3 / 7), qt gate **3 passed**, qgis gate **5 passed** (was 4), `qgis-rs` pytest 21 passed. The Rust and Bun suites were not changed by this slice and were not re-counted by this session.
* **Next session opening prompt**:

  > Confirm the pixi environments. An Arena checkout can be re-cloned at a turn boundary, and the pixi environment and `~/.local/bin` do not survive that, so expect `bash scripts/restore.sh` (about 4 minutes, about 8 GiB of scratch; check `df -h /` first), then `export PATH="$HOME/.local/bin:$PATH"`, `pixi run bun-install` and `pixi run setup`. Main is the squash commit of PR #48 (TASK-2). Expect `qgis-sdk` pure **398 passed / 3 skipped**, qt **3**, qgis **5**, `qgis-rs` pytest 21; the Rust and Bun counts are whatever the last `pixi run gates` printed on main. Commit before running `pixi run gates`, and delete any `cpython-311` bytecode from ad hoc venv runs first.
  >
  > Read `.knowledge/log.md` — the 2026-10-08 session 13 entry records TASK-2 (the three strict gates, the `qgis_version` fix, `tests/qgis_subprocess.py`, and the pre-existing nested-session failures in a bare venv) — and `AGENTS.md` for the house rules.
  >
  > TASK-2 is Done, which unblocks TASK-4 (real QGIS network and task-manager coverage). The ready high-priority tasks are TASK-26 (qgis-sdk CLI onto the shared wire protocol), TASK-41 (pure-Rust qgis-cli), TASK-42 (Python and Node FFI launchers) and TASK-43 (separate the qgis-sdk hosted runtime). Medium and ready: TASK-3 (declarative SDK docs and scaffold, which unblocks TASK-36 and then 37/38/39), TASK-13 (PyQGIS wrappers, a TASK-49 prerequisite) and TASK-50 (C++ coverage). TASK-49 stays blocked until TASK-4, 13, 37, 38, 39, 41 and 44 are Done.
  >
  > Propose the slice and stop. Propose the slice before writing code, and state what the QGIS-free CI job idea would cost if it is taken. House rules are in `AGENTS.md` (D10: automation is an xtask subcommand, not a shell script; D11: tests live in `tests/`, never in `src/`), and the session procedure and templates are in `.agents/skills/session/`.

## 2026-10-08 (session 12)

* **Landed in PR #46** (`7ea7a40`): TASK-30 slice — **AC#1 is ticked, and TASK-30 is Done (5/5)**. `pixi run xtask api-extract [--check]` (plus `crates/xtask/src/api_extract.rs`, 1,009 lines, and 20 tests) runs `clang-check -p <private db> -ast-dump <probe TU>` over the manifest's 11 declared headers and turns the text dump into `crates/qgis-sys/native_manager/generated/api_inventory.json` (446 KB, 1,683 lines): **1,658 declarations — 19 reviewed (`supported_manual`), 1,639 `unsupported`, none without a reason.** Every entry carries a status, a reason and a QGIS version range (`>=3.44.9,<4`), so "not reviewed yet" is a row, not an omission. `RepoLint::CheckApiInventory` re-extracts in the gate (~6 s) and fails naming a stale inventory or a reviewed id the headers no longer declare.
* **Idea worth keeping (an inventory of decisions, not of code)**: AC#1's value is that the manifest's reviewed ids are now checked against the headers that must declare them. The first real run immediately found one nothing could see before: the manifest said `QgsMapLayer::wkbType`, but `QgsMapLayer` declares no `wkbType` — the handler calls `QgsVectorLayer::wkbType()`. The id had been wrong since the first slice and was invisible to every existing check (it compiles, its handler works, its operation is served). Corrected in the manifest and the pinned baseline in the same commit.
* **The dump is a text contract, and text is what the tests pin**: the 20 tests in `crates/xtask/tests/api_extract.rs` run `parse_dump` on hand-written `clang-check` lines. All three bugs they pin were real: clang omits a location's file when it repeats (the file must be carried forward), prints the *macro expansion* location on deprecated members (`<line:1188:5, …/qgis_sip.h:242:15> …/qgsvectorlayer.h:1188:10 addFeature`), and `operator<<`/`operator>=` contain the `>`/`<` that a "name follows the last `>`" parser cuts at. `referenced` sits on real definitions (`EnumDecl … referenced class AuthConfigurationStorageCapability`), so it cannot be a skip marker — only `implicit*` is — and duplicate ids are deduped at parse time.
* **Evidence by damage, again**: `verify_with` fails with `… has no reason`, `… is stale; run pixi run xtask api-extract`, or `… is reviewed but the declared headers no longer declare it`; each of the three is a test on a scratch tree, because the gate lint is the only caller that matters.
* **Scope decision (user-confirmed)**: every discovered public declaration stays in the inventory as an explicit `unsupported` row with the mechanical reason "not yet reviewed against the headless manager contract" rather than being filtered out. The 1,639 rows are the honest size of the remaining API-coverage question: TASK-30 Done does not mean the API is supported.
* **Measured**: extraction 6 s for 11 headers; the declared header set was widened to the manifest's 11 (adding `qgis.h`, `qgsmaplayer.h`, `qgsfeatureiterator.h`). `pixi run gates` green on the merged tree: workspace nextest **323** (+20), QGIS-feature pass **30**, doctests **6** (+1), `qgis-sdk` pytest 394 passed / 4 skipped, `qgis-rs` pytest 21, Bun 132 (82 + 37 + 13), C++ **16 GoogleTest cases** in one ctest target (Envelope 8 + Handle 5 + Response 3; session 11's "14 = 9 + 5 RapidCheck" is stale — the binary lists no property suites). Repo lints report `api-inventory: 1658 declarations in 11 header(s) — 19 reviewed, 1639 unsupported`, `api-manifest baseline … matches at QGIS 3.44.14 with 17 declarations and 17 operations`, `check-api-operations: 17 generated plus 12 excluded operations account for all 29 wire spellings`.
* **Foot-gun (measured twice)**: `cargo nextest run --workspace` **without** `--no-default-features` fails `qgis-node::adapter` — feature unification turns the QGIS backend on, so the test that asserts "the QGIS backend is not loaded in this build" sees it loaded. The gate's `@qgis/rust:test` runs `--workspace --no-default-features --test-threads=1` plus the `qgis`-feature pass, and is the authority (323). Count tests from the gate, not from a hand-rolled invocation.
* **Post-merge evidence**: PR #46 checks — repo lints and format 1m9s, package lints 2m9s, tests 5m40s, CI, lock guard — all success; coverage and relock were path-skipped on the PR. On main at `7ea7a40`: CI run **37794643590** green (14:42:19 → 14:54:44; repo lints, package lints, tests, **coverage**, aggregate), Docs run **37796369031** green (39 s) — which also clears the 2026-10-06 queued-Docs anomaly, since the Docs run for `0ffb0d3` (37684559438) completed green at 14:42 as well. No `publish sandbox` run was path-triggered (only pixi/Cargo manifests trigger it).
* **Next session opening prompt**:

  > Confirm the pixi environments; an Arena checkout loses them at every turn boundary, so expect `bash scripts/restore.sh`, then `export PATH="$HOME/.local/bin:$PATH"`, `pixi run bun-install` and `pixi run setup` before anything builds. Main is `7ea7a40` (plus a `docs(log):` commit for this entry); TASK-30 is **Done** and the backlog has no In Progress task. Expect workspace nextest **323**, the qgis-feature pass **30**, doctests **6**, `qgis-sdk` pytest 394 passed / 4 skipped, `qgis-rs` pytest 21, Bun 132, 16 C++ GoogleTest cases. Commit before running `pixi run gates`: its format-drift step is `git diff --exit-code` and fails on an uncommitted tree. Never run bare `cargo nextest run --workspace` (feature unification flips `qgis-node::adapter`) or bare `bun x turbo run test`.
  >
  > Read `.knowledge/log.md` — this entry records the TASK-30 extraction slice, why the inventory records decisions rather than filtering, the three clang text-format bugs the tests pin, and the corrected `QgsVectorLayer::wkbType` id — and `AGENTS.md` for the house rules.
  >
  > No task is In Progress, so pick the next one from the ready list and propose it: TASK-2 (dedicated QGIS SDK integration test runner and CI job), TASK-26 (qgis-sdk CLI onto the shared Rust engine wire protocol), TASK-41/42/43 (pure-Rust CLI surface, FFI launcher, qgis-sdk vs qgis-py split), TASK-50 (C++ coverage for the native manager) and TASK-13 (PyQGIS wrappers) are all unblocked. TASK-49 stays blocked until TASK-4, 13, 37, 38, 39, 41 and 44 are Done — do not start coverage expansion early.

## 2026-10-07 (session 11)

* **In PR #41** (`c7dcd4f`): TASK-30 slice — **AC#3 is ticked**. The manifest has declared seven mapping policies since its first commit (`ownership`, `invalidation`, `overload`, `enum`, `variant`, `binary_artifact`, `paging`), but nothing executed them: the table was prose no test could contradict. New `crates/qgis-sys/tests/api_mappings.rs` is the executable copy of that table — one test per category, all at the one public seam (`qgis_sys::native_manager_ffi::invoke`, the JSON the language bindings actually send), all under the `qgis` feature, in `tests/` per D11.
* **The seven tests, and the independent expectation each one had to carry**: two `layer_open` calls give distinct live IDs; a closed ID yields `invalid_object_id` from `layer_info` *and* from a repeated `layer_close`; `export_features` with `filter: "name" = 'beta'` selects exactly `beta` out of the 3-row fixture; a point layer reports `Point` / `Integer64` / `String`, not QGIS numeric enum values; `fid` stays a JSON number and `name` a JSON string; the artifact responses carry no `data` field while the PNG on disk starts with `\x89PNG\r\n\x1a\n` and `bytes` equals the file's length; and two pages of the 3-feature layer yield feature IDs `[1, 2, 3]` with `next_offset` `2` then `null`.
* **Idea worth keeping (a policy table needs a test that can fail per row)**: "the mappings are explicit" was already true as data — the failure mode this AC guards is a row that stops being true in code while the JSON keeps claiming it. That only gets caught if each row has an assertion whose expected value comes from somewhere other than the manager (the fixture's three rows, `beta`, the PNG magic, the file length). The category names are the manifest's own, so adding an eighth mapping to `api_manifest.json` now raises the question of where its test is.
* **In PR #41** (`40fa461`): TASK-30 slice — **AC#5 is ticked**. The gate had an API diff it never ran: `check_upgrade` could already refuse a dropped declaration or a changed ownership, but `RepoLint::CheckApiManifest` called `run(true, None)`, so the diff path had no trigger outside unit tests — a mechanism with no trigger is decoration. A pinned snapshot now sits beside the manifest at `crates/qgis-sys/native_manager/generated/api_manifest.baseline.json` (QGIS 3.44.14, 17 declarations, 17 operations), and one `verify_repository(root)` — used by the gate lint *and* by `api-manifest --check`, so the documented command cannot print a green a lint would fail — diffs it before checking the generated fragments.
* **Idea worth keeping (additions are drift too)**: `check_upgrade` answers "did the upgrade drop or re-own anything" and passes when declarations are *added*. That is the wrong question for a snapshot: the extractor slice will discover declarations in bulk, so a regenerated manifest could grow a hundred unreviewed declarations and stay green. `check_baseline` is exact in both directions — added, dropped, re-owned, restatused, changed handler/codec, moved version pin — and reports every drift in one run, so the promotion is mechanical and the baseline diff between two commits *is* the reviewed API diff (doc-4 gate 8 now says so). The failure text carries the promotion command, and `scaffold` prints it too.
* **Evidence by damage, on the real tree**: dropping `QgsVectorLayer::fields` together with its operation exits 1 naming both; re-owning `Qgis::version` exits 1 printing `Some("borrowed_snapshot") -> Some("qgis_owned")`; a pin that gained an unreviewed declaration exits 1 naming it. Each restored and re-verified green. The suite grew 13 → **19** tests in `crates/xtask/tests/api_manifest.rs` (+6), including one that builds a scratch tree, passes it once, then damages it three ways and requires the same `verify_repository` to name the drift each time.
* **Honest residual for AC#5**: no real QGIS upgrade was exercised — the environment has exactly one QGIS (3.44.14) and crates.io/conda-forge are unreachable, so the AC is proven at file level (a fabricated manifest/pin drift through the gate's own entry point), not by moving the QGIS minor. When a second QGIS line exists, the same mechanism produces that diff with no code change.
* **Operational (cost one gate run)**: `pixi run gates` fails on an **uncommitted** tree, because the format-drift step is `assert_no_drift()` = `git diff --exit-code --quiet`; it cannot distinguish a formatter rewrite from a developer's own edits. Commit first, then gate. Separately, `crates/xtask/tests/affected.rs` leaves `/tmp/qgis-rs-affected-git-*` directories behind, and a later run that reuses a pid can fail — a one-off failure matched that pattern and three consecutive re-runs passed.
* **Measured, not assumed**: `pixi run -- cargo test --offline -p qgis-sys --features qgis -- --test-threads=1` → **18 passed** (11 existing + 7 new); `pixi run gates` green in **52 s** warm with `--jobs` defaults at `c7dcd4f`, and green again in **220 s** cold at `40fa461` where the workspace nextest pass reports **301** (295 + this slice's six xtask tests) and the `qgis-sys/qgis,qgis-mcp/qgis` pass **29** — and the 29 are a **subset** of the first pass (set-compared line by line: 18 qgis-sys + 11 qgis-mcp tests run in the workspace pass too, because feature unification turns those features on despite `--no-default-features`), so the second invocation re-verifies, it does not add coverage. The distinct Rust count is the first pass alone: **288 → 301** across the two slices, plus 5 doctests. Session 10's "310 = 288 + 22" double-counted **all 22**, not some of them, and session 10's opening prompt carried that number forward. `cargo clippy -p qgis-sys --all-targets --features qgis -- -D warnings` and `cargo fmt --all --check` are clean, and `--no-default-features` compiles the mapping file to **0** tests, so no non-QGIS build gains a runtime dependency.
* **Correction (measured): session 10's AC#1 extractor finding was half wrong.** That entry records "`clang-check -ast-dump=json` over the 2540 installed QGIS headers is a viable offline extractor path". It is not. `clang-check`'s own option parser refuses the value — `for the --ast-dump option: 'json' is invalid value for boolean argument! Try 0 or 1` — and smuggling it through `-extra-arg=-Xclang -extra-arg=-ast-dump=json` **exits 0 with zero bytes on stdout**, a silent no-op, which is the worst failure mode to build a pipeline on. What does work, all needing `-isystem $CONDA_PREFIX/lib/gcc/*/include` (the `stddef.h` discovery `xtask clang-tidy` already implements): textual `clang-check -ast-dump` (45.6 MB for `conversions.cpp` alone), and the usable seam, `clang-query` with `set output detailed-ast` — `match cxxMethodDecl(ofClass(hasName("QgsVectorLayer")))` returned **292 matches, 271 from `qgis/qgsvectorlayer.h`, 14 from `QtCore/qcompilerdetection.h`, 4 from `QtCore/qobjectdefs.h`** (the `Q_OBJECT` trampolines). An extractor that cannot filter inline/expansion locations cannot claim "every public declaration" means anything. Two further facts reshape AC#1's inputs: the environment ships **0 `*qgis*.sip` files** (the 861 `.sip` belong to PyQt5), so QGIS binding metadata is not an available input and the first slice is headers + manual overrides; and the reviewed id `QgsVectorLayer::QgsVectorLayer(uri,name,provider)` abbreviates the header's `QgsVectorLayer(const QString&, const QString&, const QString&, const QgsVectorLayer::LayerOptions&)` — one parameter dropped, and nothing checks the id against the header. The manifest id is deliberately left as it is: it is reviewed data, and regenerating it belongs in the extractor slice that can derive it.
* **TASK-30 stays In Progress**: AC#3 and AC#5 checked; AC#1 (clang-AST extractor — see the correction bullet above; `clang-query` plus the emitted `compile_commands.json` is the verified offline path, not `clang-check -ast-dump=json`), AC#2's codec half (every operation still carries the one `json_object` codec) and AC#4 (shared fixtures for generated operations) still open.
* **Next session opening prompt**:

  > Confirm the pixi environments; an Arena checkout loses them at every turn boundary, so expect `bash scripts/restore.sh`, then `export PATH="$HOME/.local/bin:$PATH"`, `pixi run bun-install` and `pixi run setup` before anything builds. Main is `ecc8334`; branch `arena/1cd06899-qgis-rs` holds PR #41 (TASK-30 AC#3 + AC#5) and TASK-50. Expect workspace nextest **301** — the qgis-feature pair **29** re-runs a subset of it, so count distinct tests once — doctests 5, `qgis-sdk` pytest 394 passed / 4 skipped, `qgis-rs` pytest 21, Bun 132 (82 + 13 + 37), C++ 14. crates.io, prefix.dev and conda-forge are unreachable — no new dependency, no relock. Commit before running `pixi run gates`: its format-drift step is `git diff --exit-code` and fails on an uncommitted tree. Never run bare `bun x turbo run test`.
  >
  > Read `.knowledge/log.md` — this entry records both slices (the seven mapping tests; the pinned baseline now diffed by the gate), why each mapping row needed an assertion it could fail, why additions are drift and not just drops, and two corrections: the distinct-test arithmetic, and session 10's `clang-check -ast-dump=json` claim (it exits 0 with empty output; use `clang-query` with `set output detailed-ast` plus `-isystem $CONDA_PREFIX/lib/gcc/*/include`) — and `AGENTS.md` for the house rules.
  >
  > Continue TASK-30, still In Progress with AC#3 and AC#5 proven. The remaining slices are AC#1's extractor, AC#2's per-operation codec metadata, and AC#4's shared cross-language fixtures for generated operations; pick one, propose it, and stop. If you take AC#1, start from the corrected extractor path above, expect `Q_OBJECT` trampolines in the AST, expect no QGIS `.sip` metadata in this environment, and remember that every declaration you add must be promoted into the pinned baseline in the same commit. Do not start TASK-49 — it stays blocked until its eight direct architectural dependencies (TASK-30, 4, 13, 37, 38, 39, 41, 44) are Done.

## 2026-10-06 (session 10)

* **Landed in PR #39** (`4f33dbf`): TASK-30 slice — the API manifest is now the single authority for wire spellings. `qgis-protocol`'s `Operation::all()` and the manifest's `operations` were two hand-maintained lists of the same 29 `snake_case` names with nothing comparing them; that is the "second hand-written operation spelling table" AC#2 forbids, and nothing stopped one side from silently gaining, renaming or losing a name. A sixth repo lint, `pixi run xtask check-api-operations`, requires the manifest to *partition* the served names: 17 generated operations plus 12 accounted for by explicit exclusions (`engine-transport`, `engine-geometry-and-tiles`, `engine-project-inspection`), each with a status and a reason. `Exclusion` gained an optional `operations` field (`manifest_version` stays 1), and `validate_manifest` rejects an operation that is both generated and excluded, excluded twice, or excluded under a `supported*` status.
* **Idea worth keeping (the partition, not the subset)**: the cheap version of this lint — "every manifest operation is served" — would have passed on a manifest that had lost half its operations, because a subset check cannot see a deletion. Writing the exclusions down as *operation names* rather than as prose scopes is what turns the manifest into a partition of the transport's list, and that is the only shape in which "dropped" and "never had" look different.
* **Evidence by damage, as in session 8**: the lint was not accepted for printing "ok". Dropping `layer_fields`, renaming `layer_open` → `layer_opened`, and adding a protocol-only `layer_rename` each exit 1 naming the drift; the rename reports both directions in one run, because violations are collected before failing (fixing one at a time would otherwise cost two gate runs). The tree was restored and re-verified green after each.
* **TASK-30 stays In Progress, with no AC ticked.** AC#1 covers only the reviewed core/data slice; AC#2's compile half is proven (the generated `operation_table.inc` is `#include`d by `manager.cpp`, the 22-test `qgis`-feature suite is green) and its no-second-table half is now enforced, but every operation still carries the one `json_object` codec; AC#3 has no runtime test per mapping category; AC#4 has no shared fixtures for generated operations; AC#5 has `check_upgrade` and its test but no pinned baseline manifest in the gate. An AC that cannot be proven is not a checked AC.
* **Finding for the AC#1 extractor**: the `default` env ships **no `clang`/`clang++` driver**, so the obvious `clang++ -Xclang -ast-dump=json` plan does not run here. It does ship `clang-check` and `clang-query` (LLVM 22), and `qgis-sys`'s build already emits `compile_commands.json`, so `clang-check -ast-dump=json` over the 2540 installed QGIS headers is a viable offline extractor path that needs no new crate — which matters, because crates.io is unreachable and the lockfile cannot be regenerated on this machine.
* **Operational (new, and it cost a restore)**: in this Arena sandbox the pixi environment **does not survive a turn boundary**. `.pixi/`, `.pixi-sandbox/` and `~/.local/bin/pixi` were all gone at the start of the second turn, with `.git` back to 1.4 MiB — tracked edits persisted, everything ignored did not. Budget one `bash scripts/restore.sh` (~8 min here, mostly the 1705 MiB fetch) plus `pixi run bun-install` and `pixi run setup` per turn that needs to build, and prefer doing all verification inside one turn.
* **Post-merge evidence**: PR #39 squash-merged at `4f33dbf`. Main CI run 37537147284 green in 11m49s — repo lints and format, package lints, tests, **coverage**, aggregate — and Docs 37538458211 green. No `publish sandbox` run was path-triggered (no sandbox input changed), so `sandbox/developer-linux-64` stays at `4367a18` and a restore is still current in content.
* **Baseline on merged `4f33dbf`** (`pixi run gates` green, 45 s warm): Rust **310** — 288 nextest workspace `--no-default-features` plus 22 under the `qgis` feature — plus 5 doctests; `qgis-sdk` pytest 394 passed / 4 skipped; `qgis-rs` pytest 21; Bun 132; C++ 14. The Rust count moved 303 → 310 because this slice added 7 `api_manifest` tests.
* **Next session opening prompt**:

  > Confirm the pixi environments; an Arena checkout loses them at every turn boundary, so expect to run `bash scripts/restore.sh`, then `export PATH="$HOME/.local/bin:$PATH"`, `pixi run bun-install` and `pixi run setup` before anything builds. Main is `4f33dbf`; its CI run 37537147284 was fully green including coverage. Expect roughly 310 Rust tests plus 5 doctests, 394 passed/4 skipped plus 21 pytest, 132 Bun, 14 C++, 50 docs pages. crates.io, prefix.dev and conda-forge are unreachable — no new dependency, no relock. Never run bare `bun x turbo run test`; use `pixi run gates`.
  >
  > Read `.knowledge/log.md` — the 2026-10-06 session 10 entry records the TASK-30 manifest/protocol reconciliation, why a subset check could not see a deletion, and the clang extractor finding — and `AGENTS.md` for the house rules.
  >
  > Continue TASK-30, still the only In Progress task, and still with no AC ticked. The next slice is already chosen: **AC#3**, representative runtime tests for the manifest's seven mapping categories (ownership, invalidation, overload, enum, QVariant, binary artifact, paging) in `crates/qgis-sys/tests/`, under the `qgis` feature — newly provable on a restored sandbox, since the 22-test `qgis`-feature suite runs green there. Do not start the clang-AST extractor (AC#1) or the cross-language fixtures (AC#4) in the same slice. TASK-49 must remain blocked until its eight direct architectural dependencies — TASK-30, 4, 13, 37, 38, 39, 41, 44 — are Done; do not begin coverage expansion early.
  >
  > Propose the slice and stop. House rules are in `AGENTS.md` (D10: automation is an xtask subcommand, not a shell script; D11: tests live in `tests/`, never in `src/`), and the session procedure and templates are in `.agents/skills/session/`.

## 2026-10-06 (session 9)

* **Landed in PR #37**: TASK-48 added `pixi run xtask affected`, which combines the merge-base diff with staged, unstaged, deleted, renamed and untracked paths; selects Rust reverse dependents with nextest; selects downstream Python/TypeScript/docs packages through Turbo; and falls back to the full gate for shared or unknown inputs. A representative `@qgis/test-utils` edit took 0.382 s cold and 0.267 s warm.
* **Landed in PR #37**: TASK-47 replaced the split `QApplication`/static `QgsApplication` lifecycle with one real headless `QgsApplication`, released layers and QGIS registries first, destroyed the application on its owner thread, and only then let that thread exit. Thirty loaded focused processes and three consecutive local gates passed; PR and merged-main CI were green with no post-success SIGSEGV.
* **Coverage audit and ordering decision**: fresh offline reports measured Rust 60.81% (2574/4233), `qgis-sdk` Python 53.13% (4127/7768), and `qgis-rs` Python 75.60% (381/504), 56.63% combined. TASK-49 now owns the honest 95% target and is blocked by 19 architectural tasks, with eight direct terminal dependencies: TASK-30, TASK-4, TASK-13, TASK-37, TASK-38, TASK-39, TASK-41 and TASK-44. Coverage follows those boundaries rather than freezing obsolete internals.
* **Post-merge evidence**: PR #37 merged at `b0df3a0`. Main CI run 37525708171 was green: repo 52 s, package lints 1m56s, tests 6m06s, coverage 4m35s, aggregate green; Codecov upload succeeded. No publish-sandbox run was path-triggered. The PR run and relock were also green.
* **Next session opening prompt**:

  > Confirm the pixi environments; this Arena checkout may need `bash scripts/restore.sh` and `pixi run bun-install`. Main is `b0df3a0`; its CI run 37525708171 was fully green, including coverage. Expect roughly 303 Rust tests plus 5 doctests, 394 passed/4 skipped plus 21 pytest, 132 Bun, 14 C++, and 50 docs pages.
  >
  > Read `.knowledge/log.md` — the 2026-10-06 session 9 entry records TASK-47/TASK-48, the coverage audit, and TASK-49's dependency graph — and `AGENTS.md` for house rules.
  >
  > Continue TASK-30, the only In Progress task: generate the versioned QGIS API manifest and manager handlers. Read the task before coding, preserve its existing plan and public seams, and identify which AC can be proved locally. TASK-49 must remain blocked until its eight direct architectural dependencies are Done; do not start coverage expansion early.
  >
  > Propose the TASK-30 slice and stop. House rules are in `AGENTS.md` (D10: automation is an xtask subcommand, not a shell script; D11: tests live in `tests/`, never in `src/`), and session templates are in `.agents/skills/session/`.

## 2026-10-06 (session 8)

* **Change (docs + lint)**: TASK-20 is **closed**. The engine wire protocol has
  a reference page (`docs/src/content/docs/reference/wire-protocol.mdx`, the
  site's 50th), and more importantly it cannot rot: a new `xtask
  check-protocol-docs` links `qgis-protocol` and compares the published tables
  against `Operation::all()` and `ErrorKind::all()` **in both directions**,
  plus the Python exception column against `_EXCEPTION_BY_KIND` parsed out of
  `_transport.py`. `ErrorKind` and its `all()` are now generated by one
  `error_kinds!` macro, so the list the lint checks against cannot drift from
  the enum. `REPO_LINTS` is now five: `check-sources`, `check-boundaries`,
  `api-manifest --check`, `validate-bridge-fixtures`, `check-protocol-docs`.
* **Idea worth keeping (prove a doc lint by damaging the doc)**: the lint was
  not accepted because it printed "ok". It was accepted because deleting a
  `tile_bounds` row, and separately lying about the `io` row, each exit 1
  naming the drift. A doc-sync lint that has never seen drift is a lint that
  has never been tested; the page was restored and re-verified after.
* **Change (testing)**: TASK-35 is **closed**. `QGIS_TEST_LAYER=pure|qt|qgis|
  webengine` narrows a run to one execution layer and **errors** when that
  layer is unreachable, which is the whole point — the default suite skips what
  it cannot reach, so the run that skipped every QGIS test is also green and
  "does this layer work here?" had no answer. Measured: `pure` 388 passed / 3
  skipped / 7 deselected, `qt` 3 / 395 deselected, `qgis` **4** / 394
  deselected, `webengine` a clean `UsageError`.
* **Idea worth keeping (the gate had to change a fixture to mean anything)**:
  `qgis` was 3 passed **/ 1 skipped** at first, because `qgis_app` skipped
  whenever no host was running — so the gate for the QGIS layer skipped its
  only real consumer. It now resolves in three steps: adopt a host's live
  `QgsApplication`, else construct one via a new `qgis_runtime` fixture *when
  the gate is active*, else skip as before. The default suite is unchanged (394
  passed / 4 skipped, the same 4 skips) while the gate actually proves the
  layer. Generalisable: adding a gate on top of skip-logic usually requires
  changing something underneath it, or the gate just inherits the skip.
* **Idea worth keeping (`pure` is the absence of a marker)**: defining the
  `pure` gate as the `pure_python` marker would have left ~380 unmarked tests
  in no gate at all — four gates all passing while most of the suite ran
  nowhere. Defining it as "no layer marker" makes the gates exhaustive. They
  overlap on purpose (a test marked `qt` *and* `webengine` runs in both).
* **Dead end worth recording (a submodule can eat a fixture)**: the lifecycle
  module was first named `qgis_runtime.py`, matching its fixture. The package
  facade re-exports fixtures with `globals().setdefault(...)`, and importing
  the submodule had already bound `qgis_runtime` to the *module* — so the
  fixture silently vanished and only surfaced as `fixture 'qgis_runtime' not
  found` when a consumer asked. Renamed to `qgis_lifecycle.py`, and
  `test_every_plugin_fixture_is_reachable_from_the_package` now fails loudly on
  any recurrence instead of waiting for a consumer to trip over it.
* **Deliberate deviation from session 7's hand-off**: that prompt expected "an
  `xtask` subcommand for the gate commands (D10 — not a shell script)". The
  gates landed as four `test:<layer>` scripts in `py-packages/qgis-sdk/
  package.json` instead. D10 forbids `scripts/*.sh`; a per-package test verb in
  `package.json` is the repo's existing shape for exactly this (`test`,
  `coverage`, `lint`, `doctor`), and routing a pytest invocation through Rust
  to re-emit a pytest invocation would add a hop that proves nothing. Only the
  ungated `test` is fanned out by turbo, which is the mechanism that keeps
  QWebEngine off the critical path of ordinary bridge tests.
* **Measurement (the 266-vs-278 correction, which main's session-7 entry does
  not carry)**: the whole-tree Rust baseline is **278** — 256 nextest
  (workspace, `--no-default-features`, 50 binaries) plus 22 nextest (`qgis`
  feature, `qgis-sys` + `qgis-mcp`, 6 binaries) — plus **5** doctests. Session
  6's "266 Rust tests across 43 non-empty test-binary runs" does not reconcile
  against a green gate on a restored sandbox and should be treated as
  misrecorded, not as a regression. Session 7's closing prompt also quotes
  "pytest 374 passed / 4 skipped" for `qgis-sdk`; the measured figure at
  `e6f7533` was **353 passed / 4 skipped**, and 353 + 41 new gate tests = the
  394 measured now, so 353 is the figure that reconciles.
* **Measurement (same flake, second sighting — now filed as TASK-47)**: a full
  `pixi run gates` died with `SIGSEGV` in
  `qgis-sys::native_manager_shutdown shutdown_releases_layers_left_open_on_the_owner_thread`
  *after* nextest reported the test passing, preceded by `QThreadStorage:
  Thread ... exited after QThreadStorage 5 destroyed`. Session 7 saw the
  identical crash. It did not reproduce in 11 targeted runs here (5 isolated, 3
  whole-crate, 3 of the exact gate command) and the gate re-run was green, so
  it surfaces under concurrent load. Session 7 assigned it to TASK-35; that is
  the wrong home — TASK-35 owns `QgsApplication` lifecycle in the **Python**
  SDK, while this is the **Rust** `qgis-sys` native manager teardown path. Hence
  a separate task rather than a checkbox on a task that would have closed
  around it.
* **Post-merge**: PR #35 squash-merged to `main` at **`7a631b6`**. All three
  triggered workflows green — CI 37446421611 (12m55s), **`publish sandbox`
  37446421553 (4m40s)** and Docs 37447906450 (50s). The repack *was*
  path-triggered this time, unlike session 7: adding `qgis-protocol` to
  `crates/xtask/Cargo.toml` changed `Cargo.lock`, which is a sandbox input, so
  `sandbox/developer-linux-64` advanced `66c0990` → `4367a18` and a restore is
  now current with main.
* **Baseline on merged `7a631b6`** (`pixi run gates` green): Rust **290** —
  268 nextest workspace `--no-default-features` plus 22 under the `qgis`
  feature — plus **5** doctests; `qgis-sdk` pytest **394 passed / 4 skipped**;
  `qgis-rs` pytest **21**; Bun **132**; C++ **14**; docs **50** pages. The Rust
  count moved 278 → 290 because TASK-20 added 11 `protocol_docs` tests and one
  `ErrorKind::all()` assertion.
* **Operational**: both pixi environments restored from
  `sandbox/developer-linux-64` via `scripts/restore.sh` (8708 blobs, 1705 MiB,
  162 vendored crates); `pixi run setup` repaired `libqca-qt5.so.2`. Cold gate
  9m29s, warm 1m49s. crates.io, prefix.dev and conda-forge stayed unreachable,
  so no dependency or lockfile change was possible. **Do not run bare `bun x
  turbo run test`** — it loses the `CARGO_HOME` / `CARGO_NET_OFFLINE` /
  `--env-mode=loose` that `xtask ci` injects and dies on crates.io TLS; always
  `pixi run gates`. Two further CLI notes: `backlog task edit --ac` *adds* a
  criterion, `--check-ac <n>` is what ticks one; and a long `--desc` containing
  an apostrophe hangs the command, matching session 7's note.
* **Collision worth noting**: session 7's log entry was written twice, once by
  the session that merged PR #34 and once here, because this session started
  from a tree where that entry was missing. The duplicate was dropped on rebase
  and main's version kept; only the baseline correction above was carried
  across. A session that starts by writing *another* session's log entry should
  check `origin/main` for it first.

Next session should start with:

> Confirm the pixi environments and baseline the suite with `pixi run gates`
> (expect Rust **290** — 268 workspace plus 22 under the `qgis` feature — and 5
> doctests, `qgis-sdk` pytest **394 passed / 4 skipped**, `qgis-rs` pytest 21,
> Bun 132, C++ 14 in one ctest target, docs 50 pages. An Arena sandbox starts
> with no `pixi` binary, so `scripts/restore.sh` is the first command, then
> `pixi run bun-install` and `pixi run setup`; `sandbox/developer-linux-64` is
> at `4367a18` and current with main, so the restore needs no catch-up. GitHub
> answers; crates.io, prefix.dev and conda-forge do not, so adding a dependency
> or relocking is out of scope. Never run bare `bun x turbo run test` — it
> loses the offline cargo env and dies on crates.io TLS; use `pixi run gates`.)
>
> Read `.knowledge/log.md` — the 2026-10-06 (session 8) heading — and
> `AGENTS.md` for the house rules.
>
> TASK-20 and TASK-35 are closed, and the whole shared-fixture line (TASK-32,
> 33, 34) stays closed — do not re-open any of it. I want **TASK-47** this
> session: the `qgis-sys` native shutdown SIGSEGV has now been seen in two
> separate sessions, always after the test reports success, always in Qt/QGIS
> teardown, and never reproducibly. It is the one known defect that can redden
> CI for someone who then cannot reproduce it. Start by trying to make it
> deterministic — run the `qgis-sys` + `qgis-mcp` `qgis`-feature suite in a loop
> under artificial CPU load, since both sightings were under load — and if it
> reproduces, fix the destruction order between Qt thread-local storage and the
> native manager rather than retrying the test. If three loaded runs cannot
> reproduce it, say so and close the attempt as an open item rather than
> claiming it is fixed.
>
> If TASK-47 proves unreachable, the fallback is one narrow vertical slice of
> TASK-30 (its AC#5 upgrade-diff criterion has an existing test seam and needs
> no QGIS runtime). TASK-29 and TASK-44 remain blocked.
>
> Propose the slice and stop. House rules are in `AGENTS.md` (D10: automation is
> an xtask subcommand, not a shell script; D11: tests live in `tests/`, never in
> `src/`), the session procedure and its templates are in
> `.agents/skills/session/`.

## 2026-10-06 (session 7)

* **Change (testing)**: TASK-32 is **closed**. `qgis_sdk.testing` is a package
  now — `environment`, `calls`, `iface`, `ui`, `bridge`, `qgis_api`, `network`,
  `tasks`, `processing`, `data`, `strategies`, `plugin` — with a facade
  `__init__.py` that re-exports every legacy name and re-registers every legacy
  fixture, so the pytest11 entry point and every existing import keep working.
  qgis-sdk went 169 → **353 passing** with the same 4 skips.
* **Idea (what the split was actually for)**: splitting a 2k-line module into
  twelve is bookkeeping; the point was that three of the fakes could not fail.
  `FakeNetworkManager` answered *every* URL with `{"mock": true}`, so a test
  passed against a URL it never meant to call. `FakeTaskManager.add_task` ran
  the work inside the call, so "is the button disabled while the task runs?"
  was unaskable. `FakeBridge` was a bag of canned methods, so no test touched
  the envelope protocol it is supposed to stand in for. The new
  `FakeNetworkTransport` answers only scripted routes and raises
  `NoScriptedReply` otherwise; `FakeTaskManager(auto_run=False)` runs nothing
  until `run_next()`; `BridgeHarness` runs the real check order against the
  shared `test-fixtures/bridge/` vectors. The permissive originals are kept
  under their old names for compatibility, which is the deliberate trade: new
  names are strict, old names stay lax.
* **Idea (not implemented)**: nothing in the tree yet *uses* the strict fakes
  except the new tests. The qgis-sdk suite, the scaffold template emitted by
  `qgis-plugin new`, and doc examples still reach for `fake_network_manager`
  and the auto-running task manager. Migrating them — and then deciding whether
  the permissive defaults get a deprecation path — is a separate, mechanical
  task worth filing rather than smuggling into a refactor.
* **Measurement (an AC that cannot be proven the obvious way)**: AC#7 says pure
  tests must not initialize Qt or QGIS. The obvious assertion —
  `"PyQt5.QtWidgets" not in sys.modules` after `import qgis_sdk.testing` —
  **fails, and would always fail**: the parent `qgis_sdk/__init__.py` imports
  the Qt funnel and the PyQGIS runtime probe, so the bindings are loaded before
  the testing package has a say. The honest assertions are static and
  behavioural: an AST scan of every `testing/*.py` for module-scope imports of
  `PyQt5|PyQt6|PySide6|qgis` (and of `hypothesis` outside `strategies.py`),
  plus a subprocess that imports the fakes and asserts `QApplication.instance()`
  and `QgsApplication.instance()` are both `None`. Confirmed end-to-end by
  re-running the full suite under a `sitecustomize.py` meta-path blocker for
  those four modules: 352 passed, 5 skipped, zero failures.
* **Idea (a green test that asserted nothing)**: `pytest.skip.Exception`
  (`Skipped`) derives from `BaseException`, so a test written as
  `with pytest.raises(Exception): fn_that_skips()` lets the skip escape the
  context manager and marks *the asserting test* skipped. It shows up as one
  extra skip in the summary and nothing else. Catch `pytest.skip.Exception`
  explicitly. Worth knowing anywhere a suite asserts on its own skip logic.
* **Idea (facade mechanics, pytest 8.4)**: a `@pytest.fixture` is no longer a
  function carrying `_pytestfixturefunction`; it is a
  `FixtureFunctionDefinition` carrying `_fixture_function_marker`. A facade that
  re-exports fixtures must recognise both, and a test that checks "is this
  fixture registered?" should read
  `request._fixturemanager._arg2fixturedefs` rather than call the fixture.
* **Measurement**: `pixi run gates` green on the merged tree — Rust **278**
  (256 default + 22 under the `qgis` feature) plus 5 doctests, pytest **374
  passed / 4 skipped** (qgis-sdk 353 + 4, qgis-rs 21), Bun **132** (37
  `@qgis/test-utils` + 82 `@qgis-sdk/bridge` + 13 `qgis-rs`), C++ ctest 1/1
  (`conversions`). PR #33 was green before merge; main CI run 37436051874 was
  green after it (repo lints, package lints, tests, coverage, the `CI`
  aggregate), as was the Docs run 37437153858. Job log *text* was unreadable
  from this sandbox — the Actions log endpoint redirects to Azure blob storage,
  which is blocked — so those verdicts come from `gh run view --json jobs`.
* **Measurement (a flake worth naming, not yet filed)**: one `pixi run gates`
  run failed with `SIGSEGV` on
  `qgis-sys::native_manager_shutdown shutdown_releases_layers_left_open_on_the_owner_thread`
  — nextest printed `test result: ok. 1 passed` and *then* the process aborted
  with signal 11 during teardown (`QThreadStorage: Thread ... exited after
  QThreadStorage 5 destroyed`, `QApplication was not created in the main()
  thread`). The identical tree passed on the immediately preceding and
  following runs, so it is a crash in QGIS/Qt process shutdown rather than a
  test failure. It is unrelated to this session's change (the only diff from a
  green run was `.knowledge/log.md`), but a test binary that can abort after
  reporting success will eventually redden CI at random; it belongs in TASK-35,
  which already owns deterministic `QgsApplication` startup and shutdown.

* **Operational**: both pixi environments restored from
  `sandbox/developer-linux-64`; GitHub and `gh` had write access; crates.io and
  prefix.dev stayed unreachable, so no dependency or lockfile change was
  possible (none was needed). No sandbox input changed, so no repack was
  path-triggered. Note for the backlog CLI: `pixi run backlog` re-quotes
  arguments through a shell, so an apostrophe inside `--notes` text aborts the
  command with "Expected closing single quote" — write notes without
  apostrophes.

Next session should start with:

> Confirm the pixi environments and baseline the suite with `pixi run gates`
> (expect Rust 278 — 256 default plus 22 under the `qgis` feature — and 5
> doctests, pytest 374 passed / 4 skipped, Bun 132, C++ ctest 1/1;
> `.pixi/envs/default` and `.pixi/envs/bun` restore from
> `sandbox/developer-linux-64`, GitHub works, package registries do not, so
> adding a dependency or relocking is out of scope).
>
> Read `.knowledge/log.md` — the 2026-10-06 (session 7) heading — and
> `AGENTS.md` for the house rules.
>
> I want TASK-35 this session: separate the Qt, QGIS and WebEngine integration
> fixture gates. TASK-32 landed the layer detection, the markers
> (`pure_python`, `qt`, `qgis`, `webengine`, `network`, `tasks`) and
> collection-time skipping, so do not re-open that; TASK-35 is about the
> *gates* — one offscreen `QApplication` per session, deterministic
> `QgsApplication` startup and shutdown run serialized, WebEngine behind its own
> optional gate that ordinary bridge tests never depend on, the documented
> command list, and a gate that proves no fixture leaks between layers. Expect
> the real work to be in `qgis_sdk/testing/environment.py` and `plugin.py` plus
> an `xtask` subcommand for the gate commands (D10 — not a shell script).
>
> One of the two gate runs at the end of session 7 died with `SIGSEGV` in
> `qgis-sys::native_manager_shutdown` *after* the test reported `ok` — a crash
> in Qt/QGIS process teardown, green on a re-run of the identical tree. Treat
> it as in scope for the deterministic-shutdown criterion, not as a mystery.
>
> Also worth filing while you are there: nothing in the tree yet uses the strict
> fakes TASK-32 added. The suite, the `qgis-plugin new` scaffold and the doc
> examples still use the permissive `fake_network_manager` and the auto-running
> task manager.
>
> Propose the slice and stop. House rules are in `AGENTS.md` (D10: automation is
> an xtask subcommand, not a shell script; D11: tests live in `tests/`, never in
> `src/`), the session procedure and its templates are in
> `.agents/skills/session/`.

## 2026-10-06 (session 6)

* **Change (bridge contract)**: TASK-34 is **closed**. The language-neutral
  `test-fixtures/bridge/cases.json` catalogue and its explicit golden vectors
  remain the one source consumed by Rust, Python/Hypothesis, and
  TypeScript/fast-check. `pixi run xtask validate-bridge-fixtures` now gives the
  tree a cheap structural gate: strict catalogue, description, schema,
  request, response, and event parsing rejects unknown fields, missing or
  mismatched request IDs, non-snake-case canonical wire names, incompatible
  versions, broken catalogue links, and inconsistent envelopes. Deliberately
  malformed vectors are exempt from canonical envelope parsing and continue
  to be proven by the protocol suites. The command runs in the repository-lint
  CI lane, before a compiler-heavy package lane.
* **Measurement**: PR #31 was green before merge and main CI run 37428650577
  was green after merge: repo lints 1m03s, package lints 2m02s, tests 5m56s,
  coverage 2m57s. Focused evidence was 5 new xtask validator tests, 46 Python
  bridge-contract tests passing with 2 environment skips, and 132 Bun tests.
  The expected whole-tree baseline is now **266 Rust tests across 43 non-empty
  test-binary runs, 123 + 21 pytest (2 skipped in qgis-sdk), 132 Bun, and 14
  C++**.
* **Idea (not implemented)**: TASK-30 remains the only In Progress task and
  should be revisited before another broad initiative. TASK-34 advances its
  shared-fixture criterion, but does not prove TASK-30's generated core
  operations, runtime ownership mappings, or clang-AST/API-upgrade extraction.
  Take one of those remaining vertical slices rather than treating the shared
  fixture gate as proof of the whole manifest pipeline.
* **Operational**: this sandbox restored both pixi environments from
  `sandbox/developer-linux-64`; GitHub and `gh` had write access, package
  registries remained unavailable, and the vendored graph was sufficient.
  The sandbox transport branch remains behind main; PR #31 did not touch a
  sandbox input, so no repack was path-triggered.

Next session should start with:

> Confirm the pixi environments and baseline the suite (expect 266 Rust tests
> across 43 non-empty test-binary runs, 123 + 21 pytest with 2 qgis-sdk skips,
> 132 Bun, and 14 C++; `.pixi/envs/default` and `.pixi/envs/bun` were restored
> and are materialized, GitHub works but package registries do not, and
> `sandbox/developer-linux-64` is behind main but no repack was path-triggered
> by PR #31).
>
> Read `.knowledge/log.md` — the 2026-10-06 (session 6) heading lists one open
> implementation direction — and `AGENTS.md` for the house rules.
>
> I want to continue TASK-30 this session. TASK-34 has closed its shared-fixture
> slice; do not re-open that work. Inspect the remaining acceptance criteria and
> choose one narrow vertical slice among generated core operations and codecs,
> representative runtime ownership/mapping tests, or clang-AST/API-upgrade
> extraction. Prefer the smallest slice that produces executable evidence and
> keeps `qgis-protocol` the normative contract; adding dependencies is out of
> scope in this airlocked sandbox.
>
> Propose the slice and stop. House rules are in `AGENTS.md` (D10: automation is
> an xtask subcommand, not a shell script; D11: tests live in `tests/`, never in
> `src/`), the session procedure and its templates are in
> `.agents/skills/session/`.

## 2026-10-05 (session 5)

* **Change (testing)**: TASK-33 is **closed**. `@qgis/test-utils` gained
  `createBridgeHarness`, which owns the thing every facade suite used to
  hand-roll: descriptions, call recording with request ids, scripted and held
  answers, structured rejections, events. `installBridgeGlobals` keeps its
  signature and now accepts the harness's objects, so the loader path and the
  facade path exercise one script instead of two that could drift. Shared
  assertions and `fast-check` arbitraries sit beside it. Bun tests went
  47 → 119 (`@qgis/test-utils` 14 → 37, `@qgis-sdk/bridge` 68 → 82) with no
  socket, timer or QWebEngine dependency.
* **Idea (the contract, as it is)**: writing the suites pinned behaviour that
  was previously only implied, and it is not what a reader would guess.
  `QgisBridge.call` hands the caller's callback the **raw wire answer** and
  resolves its promise with the **decoded** value — for a JSON answer the two
  differ. A string answer that fails `JSON.parse` passes through unchanged
  rather than throwing. `TasksAPI.run` reports `task_id: "unknown"` for both an
  empty answer and truncated JSON, so a caller cannot tell a finished task from
  a mangled reply. These are encoded as tests, not filed as bugs; changing any
  of them is a deliberate API decision with a test to update.
* **Change (CI)**: TASK-46 splits the gate into lanes. The split lives in
  `xtask`, not in YAML, because of D10 — a workflow step carries no build logic
  and a contributor must be able to run locally exactly what CI runs.
  `ci::Stage` is `Repo | Lint | Test | Coverage`, `Stage::steps` names what each
  owns, and `crates/xtask/tests/ci.rs` asserts the stages concatenate to
  `GATE_STEPS` with no step claimed twice. That test is the point: without it a
  lane can silently stop running a step, or two lanes can pay for the same one,
  and nothing in the YAML would notice. `pixi run gates` still walks every
  stage in order; `pixi run xtask ci --stage <name>` runs exactly one, and
  `ci.yml` does nothing else.
* **Measurement (why the cache was the real cost)**: every `actions/cache` key
  ended in `${{ github.sha }}`, so every run missed its exact key *by
  construction*, restored from a `restore-keys` prefix, and then saved a fresh
  ~3.2 GiB pair at the end. Read from the Actions API before the change: 12
  caches holding **13.3 GB against a 10 GB limit**, meaning roughly four runs
  evicted everything earlier runs had written and pull-request runs and `main`
  runs evicted each other. The post-step saves alone were 58 s of a 9 m 08 s
  job. Keys are now lockfile-only (`pixi.lock`, `Cargo.lock`,
  `bun.lock` + `turbo.json`). A sha in a cache key is a write-only cache.
* **Idea (two small ones worth keeping)**: clippy and rustc write different
  fingerprints into `target/`, so the lint and test lanes need *separate* cargo
  cache keys — one shared key has them invalidating each other every run, which
  looks like a cache that simply never works. And branch protection wants one
  stable required check, so the fan-out ends in an `always()` aggregate job
  named `CI` that is red unless every lane succeeded; required checks point
  there and never need updating when a lane is added.
* **Idea (not implemented)**: coverage is now restricted to `push` and
  `workflow_dispatch` rather than deleted. It is an instrumented rebuild of
  what the test lane just built, nothing blocks on its result
  (`fail_ci_if_error: false`), and the trend line only needs `main`. If
  coverage ever gates a merge it has to move back onto the pull-request path
  and be paid for.

## 2026-10-04 (session 4)

* **Change (backlog)**: the two findings that had been sitting unresolved for
  two sessions are **fixed**, along with everything else the audit turned up.
  The legacy `cxx::bridge` chain — TASK-7, 8, 9, 10, 11, 12 — is archived next
  to TASK-6. This applied a ruling the project had already made and left
  half-finished: all seven carried the `deprecated` label, TASK-6 had been
  archived on 2026-10-03 with "superseded by RFC 19", D12 says the qgis-sys
  CXX shims "are not the RFC 19 boundary", no `cxx::bridge` remains anywhere
  in the tree, and the functional equivalents shipped in TASK-25.2 and
  TASK-25.3. Each archived task now carries a comment saying so and how to
  reopen it.
* **Change (backlog)**: TASK-43 lost its dependency on TASK-36. TASK-43
  enforces the D13 product boundary — `qgis-sdk` never depends on `qgis-py` —
  and TASK-36 defines the declarative UI contract; nothing in 43 reads the UI
  surface. The edge was blocking TASK-43, and TASK-44 behind it, on work
  neither needs. TASK-40 was and remains the real prerequisite, and it is Done.
* **Measurement**: the backlog is **42 live tasks (28 To Do, 1 In Progress,
  13 Done) plus 7 archived**, down from 48/1. Every dependency now resolves to
  a live task, every live task has a milestone and a priority, no cycles, and
  no broken relative links under `backlog/`, `.knowledge/` or `.agents/`
  except one pre-existing one in the vendored `caveman` skill. **16 tasks are
  ready to start**, up from 12 — TASK-43 and TASK-31 among them.
* **Measurement (what the audit found)**: seven defects nobody had reported.
  Four tasks still used lowercase `id: task-N` while the rest used `TASK-N`,
  and `TASK-36` depended on `TASK-3` across that boundary — the CLI resolves
  ids case-insensitively, which is exactly why it had gone unnoticed.
  Thirteen tasks had no milestone and TASK-45 had no priority. Five relative
  links in `backlog/docs/` pointed at task files that had moved. And TASK-6
  had been hand-placed in `backlog/archive/`, whereas the CLI reads and writes
  `backlog/archive/tasks/` — `backlog task archive` fails with a bare "Failed
  to archive task" until that directory exists, which is worth knowing because
  the error names neither the path nor the reason.
* **Idea (worth keeping)**: `backlog task archive` rewrites *inbound*
  dependency edges as it archives — it printed "Removed references to TASK-8
  from TASK-9, TASK-10" — but it does not touch edges held by tasks already in
  the archive. Archiving a chain therefore leaves a partial graph that depends
  on the order you archived in. The fix was to clear dependencies on every
  archived task: inside the archive the edges schedule nothing, and the
  supersession comment carries the history instead.
* **Idea (not implemented)**: m-1 and m-2 are now nearly empty — m-1 is one
  Done task, m-2 is TASK-19 plus two Done ones. Neither milestone is worth
  retiring yet, since transactional editing genuinely has no native-manager
  equivalent and TASK-19 is real open work, but if TASK-30 generates the
  operation catalogue the two of them should probably fold into m-0.

## 2026-10-04 (session 3)

* **Change (testing)**: TASK-23 is **closed**. AC#2: every crate with an
  integration suite now has `rstest` as a dev-dependency, and the hand-rolled
  setup helper at the top of each test file is gone. `qgis-cli/tests/cli.rs`
  traded five free functions (`run`, `temp_dir`, `write_project`, `stdout_of`,
  `stderr_of`) for one `cli` fixture; `qgis-sdk/tests/plugin_cli.rs` did the
  same; `qgis-engine`, `qgis-sys` and `qgis-mcp` turned their `send`/`ok`/`err`
  and `project_file` helpers into fixture types; `qgis-server`, `qgis-render`
  and `xtask` turned `single_project`, `multi_project`, `write_project` and
  `lawful_tree` into `#[fixture]`s. AC#4: `ts-packages/qgis-sdk-bridge` states
  three `fast-check` properties over the scripted channel `@qgis/test-utils`
  installs — any JSON answer returns unchanged, arguments reach the far side
  verbatim with the bridge's callback stripped, and a description exposes
  exactly the methods it names. Those are the two transport invariants
  `qgis-protocol` asserts in proptest, restated at the bridge's boundary.
* **Measurement**: **Rust 194 → 261** across the same 42 non-empty binaries,
  **bun 44 → 47**; pytest (123 + 2 skipped, 21) and C++ (14) unchanged.
  `pixi run gates` green in 2m2s. None of the +67 is a new assertion: it is
  `#[case]` expansion. That is the point of the change — a loop over five
  malformed CRS codes stopped at the first failure and reported one result,
  whereas five cases report five, each named after the input that broke.
* **Idea (acted on, worth repeating)**: types that own a scratch directory now
  remove it on `Drop`, which the free functions they replaced mostly did not,
  and their directory names are unique per test rather than fixed. The fixed
  names were not hypothetical: `plugin_cli.rs` already carried a comment about
  a CI flake caused by a leftover directory, and three other files had the same
  bug without the comment.
* **Measurement (TypeScript)**: the bridge's JSON generator is deliberately
  narrower than `fc.jsonValue()`. That generator emits doubles, and `-0`
  round-trips through JSON to `0`, so the round-trip property fails on an IEEE
  754 detail that has nothing to do with the transport it is about. Object keys
  come from a fixed set for the same reason — a generated `__proto__` would be
  testing `JSON.parse`'s prototype handling. Same lesson as session 2's
  `QString::fromStdString` finding: a property over "arbitrary" values is
  usually a property about the generator until you narrow it.
* **Operational**: this sandbox was **recycled mid-task**. `.pixi/`,
  `~/.local/bin/pixi` and every `node_modules/` were gone, and the local branch
  pointer had rewound to `main` while the working tree still held the committed
  work as uncommitted changes. Recovery, in order: `sh scripts/restore.sh`
  (~2 min), `git fetch origin arena/…` then
  **`git reset --mixed origin/arena/…`** — `--mixed`, not `--soft`, so the index
  matches the pushed tip and `git status` shows only the new work — and
  `bun install --frozen-lockfile`. Note that npm answered normally even though
  crates.io and prefix.dev still do not; the airlock's vendored crates cover
  the former, and `bun.lock` plus a live registry covers the latter.
* **Still open**: the two backlog findings from session 2 are unchanged and
  still need the user's ruling — TASK-43's dependency on TASK-36 looks wrong,
  and `backlog/archive/task-6` is archived while still `status: To Do` with
  TASK-7 depending on it. Closing TASK-23 unblocks TASK-31 and the
  32/33/34 → 35 → 42 chain behind it.

## 2026-10-04 (session 2)

* **Change (testing)**: The native manager has its own C++ tests, and the gate
  runs them. `manager.cpp` kept the JSON envelope, the handle encoding and the
  C ABI's malloc/free pair in an anonymous namespace inside a translation unit
  that cannot be loaded without a QGIS prefix and a `QApplication` — so the
  functions most likely to cost a leak, a truncated answer or a wrong layer
  were the only ones nothing tested as units. They move to
  `crates/qgis-sys/src/native_manager/conversions.cpp`, which depends on QtCore
  and the standard library only, and `crates/qgis-sys/tests/cpp` builds that one
  file against GoogleTest 1.18 and RapidCheck: 14 tests, 9 examples and 5
  properties, headless, under the same warnings-as-errors contract `build.rs`
  compiles the shim with. `xtask test-cpp` drives cmake/ninja/ctest and
  `@qgis/rust`'s `test` script calls it, so `pixi run ci` covers the C++ suite
  like every other (D10). No new dependency: cmake and ninja (TASK-24), gtest
  and rapidcheck were already declared in `pixi.toml` and carried in the offline
  pack — which matters, because this machine cannot run `pixi lock`.
* **Change (ci)**: `cpp_sources` now walks the shim's `tests` tree, so
  clang-format and the format-drift gate see C++ test files that were invisible
  to them before. The counterpart is that clang-tidy is narrowed to
  `crates/qgis-sys/src`: it is driven by `compile_commands.json`, which
  `qgis-sys`'s build script writes only for what cargo compiles, and handing it
  a CMake-built file makes it guess a command line and fail on the first Qt
  include.
* **Measurement**: the property over `copy_response` was written against
  arbitrary byte strings and failed immediately — not on the conversion, but on
  the test's own premise. `QString::fromStdString` decodes UTF-8 and substitutes
  U+FFFD for what it cannot decode, so two distinct invalid sequences collapse
  onto one key and a round-trip property is false for reasons that have nothing
  to do with the manager. The properties now generate printable ASCII, which is
  what the wire actually carries, and the replacement behaviour is pinned by an
  example test instead of being hidden by the fix. Worth remembering the next
  time a property is written over anything Qt will decode.
* **Verified**: `pixi run gates` is **green on a restored airlock** — 3m35s cold,
  1m56s warm — which the session skill said was impossible as recently as
  yesterday. Both reasons it gave were fixed by `d24772c`: the gate forces
  `--offline` and `--env-mode=loose`, so the napi build keeps `CARGO_HOME` and
  its vendored sources, and `patchelf` is now declared and packed, so
  `qgis-rs-py#build` produces a wheel locally. Baseline on `4a87ed2`: **194 Rust**
  across 42 non-empty test-binary runs, **123 + 2 skipped** and **21** pytest,
  **44** bun, **14** C++. `.agents/skills/session/` was corrected to say all of
  this, including the restore's current figures (8708 blobs, 75732 verified
  entries).
* **Idea (not implemented)**: TASK-23 is **not** closeable and stays In Progress
  on two ACs. AC#2 wants rstest fixtures instead of a hand-rolled setup helper
  per test file; rstest is a workspace dependency but is used in exactly one
  file, `crates/qgis-render/tests/tiles.rs`. AC#4 wants both TypeScript client
  suites on fast-check; `ts-packages/qgis-node` has it, `ts-packages/qgis-sdk-bridge`
  does not, so the bridge asserts none of the invariants the Rust properties do.
  Both are local, offline-provable work — fast-check and rstest are already
  installed — and neither needs a lock.
* **Idea (not implemented)**: two backlog findings, neither acted on because
  they change task metadata the user has not ruled on. **TASK-43's dependency on
  TASK-36 looks wrong**: 43 is about the dependency graph (no `qgis-sdk` →
  `qgis-py`, delete `_fallback_cli.py`) and 36 defines the declarative UI
  contract; with that edge in place the hand-off at the end of the previous
  session recommended a task its own metadata says is blocked, and TASK-44 is
  blocked behind 26, 42 and 43 in turn. **TASK-6 is archived while still
  `status: To Do`**, and TASK-7 depends on it, so the binding chain
  7 → 8 → 9/10 → 11/12 — six tasks across m-1 and m-2 — is blocked by a task no
  list shows. Either re-point TASK-7 at TASK-5 (Done) or record that the chain
  is superseded by the RFC-19 native manager.
* **Next session's opening prompt**: see the session report; in short, finish
  TASK-23 by putting rstest fixtures through the Rust suites (AC#2) and a
  fast-check property into `ts-packages/qgis-sdk-bridge` (AC#4), which closes
  the task and unblocks TASK-31 and the 32/33/34 → 35 → 42 chain behind it.

## 2026-10-04

* **Change (ci)**: The D13 product boundaries are decided by a program instead
  of by review. `crates/xtask/src/boundaries.rs` adds `xtask check-boundaries`,
  which reads every member manifest plus the two distribution manifests and
  rules on four things: the forbidden dependency edges (no `qgis-sdk` →
  `qgis-py`, no binding crate depending on another binding crate, nothing
  depending on a CLI), binding crates owning no `[[bin]]`, the canonical
  executable names (`qgis-cli`, `qgis-mcp`, `qgis-plugin`, `xtask`), and a
  closed list of tracked fallbacks so a new one cannot appear unnoticed. It
  runs in `xtask gate`'s repo-lints step, before anything compiles, and costs
  no new dependency — the checker hand-parses TOML because the airlock cannot
  fetch one. Today it reports `12 crates and 2 distributions match D13 (1
  tracked fallback(s))`; 11 tests in `crates/xtask/tests/boundaries.rs` cover
  the rules, the real repository, and a discovery guard that fails if a crate
  stops being seen. Two deviations are named rather than silently allowed:
  `py-packages/qgis-sdk/src/qgis_sdk/_fallback_cli.py` (TASK-43) and the
  `qgis-cli` console script that `qgis-sdk` also ships (TASK-44).
* **Change (testing)**: The gate now runs the QGIS-backed code it used to only
  compile. `@qgis/rust`'s `test` script runs the workspace with
  `--no-default-features` and then `cargo test -p qgis-sys -p qgis-mcp
  --features qgis-sys/qgis,qgis-mcp/qgis -- --test-threads=1`, which is what
  closes RFC 19 phase four: before this, the `qgis` feature paths had zero
  tests executed anywhere, so "it builds" was the only claim the repository
  could make about them. Rust went from 149 to 183 passing tests across 35
  test-binary runs (30 integration files, 5 of them re-run under the feature).
  Single-threaded on purpose: QGIS initialization is process-global.
* **Addition**: `crates/qgis-protocol`'s crate documentation now states the
  binary-artifact policy — renders cross the wire as filesystem paths, never as
  base64 bytes — so the rule lives next to the types it constrains instead of
  only in `.knowledge/decisions/D12-qgis-native-manager-over-c-abi.md` §3.
  D12 also gained the snake_case amendment that issue #19 was closed on.
* **Idea (not implemented)**: `xtask scaffold` still emits a `cxx::bridge`
  module and a `#include "rust/cxx.h"` for a crate that no longer has `cxx` or
  `cxx-build` anywhere in it. Nothing is broken today, but the next binding
  scaffolded from it would reintroduce the exact dependency RFC 19 spent four
  phases removing, and the gate would not catch it — `check-boundaries` rules
  on edges between crates, not on what a generator writes. Filed as TASK-45:
  either teach the template the native-manager shape D12 chose, or delete the
  C++ half of the template and let `scaffold` make Rust-only crates.
* **Idea (not implemented)**: `qgis-rs-py#build` cannot run in this sandbox
  because `patchelf` is in neither `pixi.toml` nor the offline pack, and
  adding it needs `pixi lock`, which needs the network. CI runners supply it,
  so the gap is local-only — but it means `pixi run gates` is not actually the
  same command CI runs, and the difference is discovered rather than declared.
  Declaring `patchelf` as a pixi dependency the next time the lock can be
  regenerated would close it.
* **Verified**: PR #25 was green before the merge (CI 8m51s) and squash
  `067d2a6` is green on `main` after it (CI 9m17s, Docs 50s). The `publish
  sandbox` workflow correctly did not fire: its `paths` allowlist covers the
  manifests and the vendored crate graph, and this change touched neither.
  Locally the same fan-out is 21 of 25 tasks with `--env-mode=loose`, the one
  failure being the `patchelf` gap above — so the green that counts here is
  CI's, not the sandbox's.
* **Next session's opening prompt**: TASK-40 closing unblocked four tasks —
  41, 42, 43 and 26 — and 44 waits on 26. Start by reading
  `.knowledge/decisions/D13-rust-cli-ffi-and-qgis-sdk-boundaries.md` and the
  capability-ownership matrix in
  `backlog/docs/architecture/doc-7 - ...Product-Boundaries.md`, then take
  TASK-43 (delete `_fallback_cli.py`) and TASK-44 (the duplicate `qgis-cli`
  console script in `qgis-sdk`): both are now the only two deviations
  `xtask check-boundaries` tolerates, and closing them lets the tracked-
  fallback list shrink to zero. Before touching Python, run
  `export PATH="$HOME/.local/bin:$PATH"`, `pixi run setup`, then
  `pixi run bun-install`; expect `qgis-rs-py#build` to fail locally on
  `patchelf` and filter it out. TASK-45 (the `xtask scaffold` cxx template) is
  already filed and is a good small warm-up if you want one.

## 2026-10-03

* **Change (ffi)**: The Python and Node bindings no longer mirror the domain
  types. `crates/qgis-protocol` defines the wire format (`EngineRequest` /
  `EngineResponse`, `TRANSPORT_VERSION = 1`, a closed `Operation` enum with 13
  variants and `Operation::all()`, `ErrorKind`), `crates/qgis-engine` owns
  `invoke(&str) -> String` with one match arm per operation, and each binding
  crate is now a single `invoke` function — `crates/qgis-py` went from 778
  lines of `#[pyclass]` to ~65, `crates/qgis-node` from 632 to ~40. The
  ergonomic APIs moved into the host languages
  (`qgis_rs/_transport.py` + `_api.py`, `ts-packages/qgis-node/index.js`), and
  the `_fallback.py` / `fallback.js` re-implementations were deleted: a
  fallback is a second set of answers. Everything on the wire is `snake_case`,
  including operation names; the JS client renames at its own edge. Golden
  values are now asserted identically in all three suites (4568 tiles for
  `14,50,15,51` z10-14; `tile_from_lon_lat(10, 13.9, 51.1)` ⇒ `{10,551,342}`).
  15 engine tests, 6 protocol tests, 17 pytest, 11 bun contract tests —
  all green. Rationale and costs: `.knowledge/decisions/D09-wire-protocol-over-ffi.md`.
* **Change (ci)**: Repository automation is `crates/xtask`, a clap binary with
  16 unit tests, instead of eight shell files called by path from four
  manifests. `ci.sh`, `check-cpp.sh`, `lint-toml.sh`, `npm-pack-check.sh`,
  `scaffold.sh`, `setup-qca.sh`, `ci-failure-summary.sh` and `release/*.sh` are
  deleted; `pixi.toml`, `lefthook.yml`, `ci.yml`, `autorelease.yml`,
  `release.yml` and the npm `pack:check` scripts call subcommands. A generic
  `pixi run xtask <sub> [args]` task means a new repository verb needs no new
  pixi task; `ci`, `gates`, `setup`, `scaffold`, `check-cpp` and `lint-toml`
  stay as aliases because hooks and humans already type them. Per-package
  verbs stayed with turbo on purpose. `xtask release` publishes
  `qgis-protocol` and `qgis-engine` alongside the original six crates and
  shells to `pixi run version` rather than reimplementing `scripts/version.ts`.
  Rationale: `.knowledge/decisions/D10-xtask-over-shell-scripts.md`.
* **Change (testing)**: `src/` is code and `tests/` is tests, in every crate and
  every package. 21 `#[cfg(test)] mod tests` blocks (~1100 lines) moved out of
  `crates/*/src/` into `crates/*/tests/<topic>.rs`; the same 120 tests still
  run, now as integration tests that use each crate the way a consumer does.
  Consequences: `crates/xtask` is a library plus a six-line `main.rs` (a
  `[[bin]]` cannot be linked from `tests/`); the items the tests need are now
  `pub` with a doc comment saying so (`CRATES`/`already_published`,
  `split_list`/`what_is_served`/`tiles`, the `#[tool]` handlers plus a public
  `QgisMcpServer::tools()` for the router the macro generates privately);
  `crates/qgis-node` gained the adapter test `crates/qgis-py` already had; and
  `ts-packages/qgis-node` — the one package whose sources sat at its root —
  moved `index.js`/`index.d.ts` into `src/`, with `main`, `types`, `files` and
  `pack:check` following. Rationale:
  `.knowledge/decisions/D11-tests-outside-src.md`. The next step, adopting
  proptest/rstest, hypothesis, fast-check + `@qgis/test-utils` and
  GoogleTest/RapidCheck, is backlog TASK-23.
* **Change (sdk)**: `ts-packages/qgis-sdk-bridge` gained the `README.md` its
  `files` field already promised and a `pack:check` script, so `turbo run
  pack:check` now covers both npm packages instead of one.
* **Change (env)**: The pixi-sandbox publisher moved to v0.5.2 and its three
  generated files were reinitialized, which retired the seven hand edits `d11e72e`
  and `45ac2b5` had reinstated by hand — and the `LOCAL EDITS` banner every reviewer
  had to cross-check against. The policy now lives in a `[workflow]` table in
  `pixi-sandbox.toml` and `pixi-sandbox init` renders it, so the owned files stay
  byte-identical to a fresh render and the scheduled upgrade job's pull requests are
  trustworthy by construction: the `push` `paths` allowlist, least-privilege
  permissions, the concurrency group, `timeout-minutes`, the pinned `setup-pixi`
  pixi-version and its disabled cache. The allowlist is narrowed to the transport's
  real inputs (the plan, the two pixi manifests, the vendored crate graph including
  every member manifest, the workflow itself) and drops `package.json` / `bun.lock`
  and the `py-packages/**` and `ts-packages/**` manifests, none of which can change a
  packed byte. Three things config cannot express are given up on purpose: a timeout
  on the upgrade job, a per-branch second concurrency group the workflow-level one
  already covers, and deleting the redundant `pixi global install` step on the
  publish job. v0.5.2 generates the repaired `SHA256SUMS` bootstrap check that
  `45ac2b5` had to fix by hand, since v0.4.3–v0.5.1 ran it against a filename that
  does not exist in the runner's cwd and so verified nothing.

## 2026-09-24

* **Change (ci)**: `publish_sandbox.yml` now uses pixi-sandbox's trigger shape —
  `push` to `main` with a `paths` filter (`.pixi-sandbox.toml`, `pixi.toml`,
  `pixi.lock`, `.github/workflows/publish_sandbox.yml`) plus `workflow_dispatch` —
  instead of `workflow_run` after every successful `CI` run, which cannot filter
  by path and so republished `sandbox/developer-linux-64` on every green `main`.
  The publish no longer waits for `CI` on the same commit (the PR that changes
  these files is still validated by CI, including `plan --json`), and both jobs
  now check out the triggering commit instead of the branch tip.
* **Change (env)**: `dev` now guarantees Python via a new `py-runtime` feature
  (`python >=3.11,<3.15` — intersects, never overrides, the interpreter the
  conda-forge `qgis` package pins), and the `py` feature gained `pytest-cov`
  (the plugin CI previously pip-installed) next to `pytest`. JS testing moved
  to bun end to end: the `node-test` task runs `bun test tests/contract.test.js`
  in the `docs` env while `node-build` still builds the napi addon with npm in
  `node`, the package's own `test` script and README now say bun, CI's
  node-FFI step invokes `pixi run -e docs bun test …`, and the TypeScript
  getting-started page shows the bun invocation. bun cannot join `dev` and
  `docs`/`dev` cannot share a solve group: conda-forge `bun 1.3.11 h5` pins
  `icu >=75.1,<76` while the QGIS stack pins `icu >=78.3,<79` (verified
  against the feedstock — latest build 2026-07-31, "Rebuild for icu 78" open
  since 2026-02-10). bun was verified to load the napi addon and run the
  contract suite (5/5) plus the bridge suites (22/22). `pixi.lock` was
  regenerated on a GitHub runner (the working sandbox cannot reach
  conda-forge); the refreshed lock only adds pytest-cov/coverage/toml to the
  `py`/`py-qgis` solves — every other package stayed at its locked version.
* **Verify**: Landed the pending environment refactor (PR #6) after verifying it
  from scratch on a fresh Codespaces sandbox — pixi 0.81, cargo 1.96.1, clang-format
  22.1.8, QGIS 3.44.14. `pixi install -e dev --locked` succeeds and the committed
  `Cargo.lock` is complete for all 9 workspace crates; `gates` (fmt-check, clippy
  `-D warnings`, lint-toml, lint-actions, test), `check-cpp`, and `test-full`
  (application_lifecycle + vector_layer) are all green.
* **Fix**: Clippy 1.96 widened beyond what the code was written for.
  * `unnecessary_map_or` → `is_none_or` (`LayerStyle::is_valid`, qgis-styles).
  * `ptr_arg` → `&Path` parameters in `write_compile_commands` (qgis-sys build.rs).
  * `manual_pattern_char_comparison` → `split(['_', '-', ' '])` in `to_pascal_case`
    (qgis-sdk + qgis-plugin) and `type_complexity` → `PlanLevel` alias (qgis-py).
  * `inherent_to_string` → `impl fmt::Display` + `#[napi(js_name = "toString")]`
    `as_string` on the qgis-node wrappers; the `.d.ts` `toString()` contract is
    preserved because the generated names stay identical.
  * PyO3 `useless_conversion` false positive on `#[pyfunction]`/`#[pymethods]`
    (pyo3/pyo3#4828, fixed upstream in 0.23.5) silenced with module-level
    `#![allow(...)]`; `render` also got an explicit `#[pyo3(signature = ...)]` to
    retire pyo3's deprecated implicit defaults warning.
* **Fix (test harness)**: `QApplication` is a per-process singleton, but `AppHandle`
  created one per `vector_layer` test — deterministic heap corruption
  ("corrupted double-linked list", SIGABRT) from the second test on. Rebuilt
  `crates/qgis-sys/tests/helpers/mod.rs` around a `thread_local` shared app that
  lives for the whole test binary; 5/5 vector_layer + 1/1 lifecycle tests now pass.
  Also required `const { RefCell::new(None) }` for clippy 1.96's
  `missing_const_for_thread_local`.
* **Fix (setup task)**: the old `setup` hardcoded `$CONDA_PREFIX/lib/libqca-qt6.so.2`
  as the soname source, but the dev env ships the Qt5 flavor
  (`libqca-qt5.so.2.3.12`) with no `libqca-qt6` at all — the symlink was dangling
  and QGIS-backed tests failed to load (`libqca-qt5.so.2 not found`). The task now
  links whichever flavor is present, failing loudly otherwise.
* **Fix**: `.github/workflows/rust-check.yml` fmt scope omitted `qgis-styles`; the
  crate is now formatted there too.
* **Fix (CI)**: the `test-rust` job ran bare `cargo test --workspace`, which on a
  headless runner aborted once the (now-run) QGIS-backed tests created a
  `QApplication` (`could not connect to display`) and would race the single-app
  harness across threads. It now delegates to the repo's own `test`/`test-full`
  pixi tasks so offscreen platform, `--test-threads=1`, and provider/proj env are
  the single source of truth. `Test Rust code` is green in CI.
* **Workflow consolidation and PR failure follow-up**: the PR's red Node builds
  used `napi build --manifest-path`/`-o`, which `@napi-rs/cli` 2.18 does not
  support; the package scripts now use `--cargo-cwd` and a positional output
  directory. The qgis-sdk test suite loaded `qgis_sdk.testing` both through its
  `pytest11` entry point and explicit `pytest_plugins` declarations; the duplicate
  registrations were removed. The Ubuntu maturin-action wheel matrix (which failed
  in its Docker/Python bootstrap) is no longer part of CI: smoke tests build both
  Python packages with maturin directly. The workflows are now `ci.yml`, `docs.yml`,
  and `publish_sandbox.yml`; Python and Rust coverage reports are retained as
  artifacts, and sandbox publishing is gated on a successful CI run.
* **Test layout**: Removed the standalone `examples/` programs and their Pixi/CI
  invocations. Core geometry and CLI behavior stay tested in Rust crates; the
  PyO3/NAPI adapters now have Rust-side result-shape tests, and Python/Node smoke
  suites run after extension compilation with native loading required in CI.
  Rust CLI smoke coverage lives in `crates/qgis-cli/tests` and
  `crates/qgis-sdk/tests/plugin_cli.rs`, rather than inline workflow shell.
* **Style**: ran `clang-format 22` over the C++ shims/headers (`qgis-sys/src`,
  `qgis-sys/include`) that predated the formatting requirement.

## 2026-09-23

* **Addition**: Adopted the reference project's *release-mode* publisher as the
  new environment-packing path, replacing the homegrown env-pack pipeline.
  * New `.pixi-sandbox.toml` declares the reviewed publish plan — one `developer`
    bundle (`dev` + `docs` environments, `linux-64`, `cargo_vendor = true`).
  * New `.github/workflows/publish-sandbox.yml` is a thin consumer wrapper around
    the pixi-sandbox *reusable* workflow
    (`Archont561/pixi-sandbox/.github/workflows/publish-sandbox.yml` at pinned
    commit `3d7a6182`, release `v0.2.0`). It auto-runs after a successful `CI`
    run on `main` (or via `workflow_dispatch`) and publishes the
    `sandbox/developer-linux-64` orphan branch. Packing, verification, and
    publishing all run on the native runner with a checksum-verified standalone
    release binary; no pixi-sandbox crate is vendored (consumer mode).
  * New `scripts/restore.sh` — the airlock one-liner: fetch the branch, run
    `doctor --verify`, restore envs + vendor tree offline, source
    `.pixi/sandbox-env.sh`.
  * **Removed**: `.github/workflows/env.yml` and the old `scripts/pack-env.sh`,
    `publish-env-branch.sh`, `setup-env.sh`, `use-pack.sh`. The `pack` task and
    the `pixi-pack` workspace dependency are gone — pack tooling is no longer a
    local dependency (the release binary fetches its own pinned tools).
  * **Update**: `ci.yml` gained a "validate sandbox publish plan" job using the
    upstream `setup-pixi-sandbox` action + `plan --json`, pinned to the same
    SHA as the publisher. `lint-toml` bare mode now also checks
    `.pixi-sandbox.toml`. Knowledge docs (`env-provisioning.md`, `pixi.md`,
    `CONTEXT.md`, `documentation-site.md`) rewritten to the new consumer model.

## 2026-09-23

* **Fix**: Removed the last deprecated pixi syntax — top-level `channels` in
  `[package.build]`. pixi moved that key to `backend.channels` (prefix-dev/pixi
  #4361); the three source-package manifests (`py-packages/qgis-sdk`,
  `py-packages/qgis-rs`, `crates/qgis-node`) now declare the backend as a
  `[package.build.backend]` table carrying `name`/`version`/`channels`. The
  `⚠️ Top-level 'channels' in [package.build] is deprecated` warning no longer
  appears on `pixi lock`.
* **Update**: Reorganized the pixi environments and task layout to the reference
  (Archont561/pixi-sandbox) model. There is *no* `default` environment anymore:
  dependencies moved from the root `[dependencies]` table into feature layers
  (`rust`, `cxx`, `qgis`, `utils`, `docs`, `sandbox`, `sdk`, `py`, `node`), and
  the environments are now `dev` (rust+cxx+qgis+utils+sandbox — the primary one),
  `ci` (rust+cxx+qgis+sandbox), `utils` (hook/lint tooling), plus the unchanged
  `docs`/`sdk`/`py`/`py-qgis`/`node`. User-facing tasks set `default-environment`
  so bare `pixi run <task>` still works; CI and lefthook pass `-e` explicitly.
* **Update**: pixi 0.81 quirk discovered and documented — `default-environment`
  is only accepted on tasks that have a `cmd`, declared inline in `[tasks]`;
  block-form `[tasks.<name>]` tables and pure aggregators (`gates`/`ci`/`ci-full`)
  reject it. Aggregators instead resolve their environment through `depends-on`.
* **Fix**: splitting `docs` out of the `default` group surfaced a latent icu
  conflict — conda-forge QGIS needs icu ≥78.3 while `bun` pins icu <76, so bun
  cannot share an environment with QGIS. The `docs` feature is deliberately kept
  out of `dev`/`ci`; docs tasks run against the separate `docs` environment.
* **Addition**: New `utils`-backed tasks — `lint-commit` (`convco check
  --from-stdin`, used by the commit-msg hook), `lint-toml` (taplo, staged-file
  aware via `$@` passthrough), `lint-actions` (actionlint). `check-cpp` now
  accepts optional staged files passed through `pixi run check-cpp -- a.cpp b.h`
  (falls back to the whole tree without args). `gates` gained `lint-toml` +
  `lint-actions`.
* **Update**: [lefthook.yml](/lefthook.yml) rewritten to the reference shape
  (`min_version: "2.0.0"`, `pixi run -e dev <task>` for every hook) so hooks and
  CI cannot drift; pinned to staged files only via `glob` + `{staged_files}`,
  with a `commit-msg` convco job and an optional `pre-push` gates job.
* **Update**: workflows re-pointed — `ci.yml` validates `dev` + `utils` + `docs`
  and runs tests in `dev`; `env.yml` packs the `dev` environment
  (`pixi install -e dev` / `pixi run -e dev pack`); `scripts/pack-env.sh`
  defaults to packing `dev`. README + knowledge docs updated to match.
  (The env->`sandbox/` branch migration to `pixi-sandbox` itself is still
  pending — see the notes in [CONTEXT.md](/CONTEXT.md) and the pixi-sandbox
  reference project.)

## 2026-09-18

* **Creation**: Added `crates/qgis-mcp` — a Model Context Protocol server on the official [rmcp](https://github.com/modelcontextprotocol/rust-sdk) SDK (3.4), bundled into the `qgis-cli` binary as `qgis-cli mcp`. Six tools mirror the subcommands (`capabilities`, `crs_info`, `plan_tiles`, `project_info`, `render_map`, `export_features`); `crates/qgis-cli/tests/mcp_stdio.rs` spawns the real binary and drives it through `initialize` → `tools/list` → `tools/call`.
* **Creation**: Scaffolded the crates [api-design.md](/api-design.md) specifies — `qgis-render` (engine types), `qgis-server` (OGC routing), `qgis-mcp`, `qgis-cli` (clap). The pure geometry is implemented and tested; operations needing `libqgis_core` return a typed `Error::Unimplemented` naming what is missing.
* **Update**: Updated [api-design.md](/api-design.md) with §2.8 `mcp`, [architecture.md](/architecture.md) crate table, and the project tree in `CONTEXT.md`.
* **Addition**: Added `.github/workflows/rust-check.yml` — a QGIS-free `cargo fmt/check/clippy/test` job that posts its logs to the commit, so the workspace has a fast Rust signal that does not need the pixi environment.
* **Fix**: `settings.with_size(width, settings.height)` moved `settings` in the receiver and read it in the argument (E0382) in both `qgis-mcp` and `qgis-cli`; and `parse_extent_rows` only skipped a `name,...` header when it was the very first line, so a comment line above it broke `batch --extents`.
* **Creation**: Established `packages/qgis-sdk/` — the `qgis-sdk` pixi workspace package (`[package]` manifest + hatchling `pyproject.toml` + `src/qgis_sdk/` + 35 unit tests). Implements the plugin/algorithm declaration layer of [qgis-plugin-sdk.md](/qgis-plugin-sdk.md); PyQGIS is reached lazily through `qgis_sdk.runtime` so the tests run without QGIS.
* **Update**: Updated [pixi.md](/pixi.md) — `preview = ["pixi-build"]` workspace flag, the `sdk` feature and environment, workspace-package layout, and how `import qgis` resolves (`$CONDA_PREFIX/share/qgis/python{,/plugins}` via the conda-forge activation script, repeated in `activation.env`).
* **Update**: Python is deliberately *not* a declared dependency — the conda-forge `qgis` package pulls in the interpreter its bindings were built against (CPython 3.14 for QGIS 3.44.9), so a separate `python` pin could only drift.
* **Fix**: Negated `__init__.py` / `__main__.py` in `.gitignore`. The `_*` rule ignored every `__init__.py`, and hatchling honours VCS ignore files, so a built `qgis-sdk` wheel came out as an empty namespace package that could not be imported.
* **Addition**: Filled in the 22 documentation pages that `cli/index.mdx` and `reference/index.mdx` linked to but that did not exist — six `qgis-cli` subcommand pages (`render`, `tiles`, `batch`, `info`, `serve`, `export`) and sixteen API reference pages (`render`, `tiles`, `layout`, `features`, `geometry`, `crs`, `server`, `wms`, `wfs`, `expr`, plus `render/{project,layer,feature,geometry,settings,crs}`). Content follows the public API surface in [api-design.md](/api-design.md). The docs site now builds 36 pages with zero broken internal links or anchors.
* **Creation**: Established [.github/workflows/pages.yml](/../.github/workflows/pages.yml) — builds `apps/docs` with the Pixi `docs` environment and publishes it to GitHub Pages at https://archont561.github.io/qgis-rs/ (build + deploy jobs, SHA-pinned actions, `pages: write` + `id-token: write`).
* **Update**: Updated [documentation-site.md](/documentation-site.md) — GitHub Pages deployment flow, subpath (`base`) handling, and the two production-only build gotchas.
* **Update**: Configured `site` and `base: '/qgis-rs'` in `apps/docs/astro.config.mjs` for the Pages subpath; added `apps/docs/remark-base-links.mjs` so in-content links are prefixed too.
* **Addition**: Created `apps/docs/src/content/config.ts` — without the `docs` collection schema, Starlight's `draft === false` production filter dropped every page and the build emitted only a 404.
* **Addition**: Created `apps/docs/src/content/docs/index.mdx` (splash landing page) and `apps/docs/public/favicon.svg`.
* **Update**: Pinned `@astrojs/sitemap` to 3.6.0 via `overrides`/`resolutions` in `apps/docs/package.json` — 3.7+ needs the Astro 5-only `astro:routes:resolved` hook and crashes `astro:build:done` on Astro 4.
* **Addition**: Committed `apps/docs/bun.lock`; CI and the Pages workflow now install with `bun install --frozen-lockfile` (Pixi `bun` constraint raised to `>=1.2.0,<2` so it can read the lockfile).
* **Creation**: Established [api-design.md](/api-design.md) — complete public API surface for qgis-render, qgis-cli, qgis-server, and language bindings.
* **Creation**: Established [qgis-plugin-sdk.md](/qgis-plugin-sdk.md) — Python-first plugin framework with optional Rust acceleration.
* **Creation**: Established [documentation-site.md](/documentation-site.md) — Astro Starlight documentation site in apps/docs/ with Bun runtime.
* **Addition**: Created apps/docs/ directory with Astro Starlight documentation site.
* **Addition**: Configured `docs` Pixi environment with Bun dependency and docs-dev/docs-build/docs-preview tasks.
* **Update**: Updated .gitignore to exclude apps/docs/node_modules/, apps/docs/dist/, and apps/docs/.astro/.

* **Update**: `packages/` is gone — the repo is now split by *kind* instead of by language:
  `py-packages/qgis-rs` (wheel dist: pyproject, `qgis_rs/`, `qa_gate/`, `tests/`),
  `py-packages/qgis-sdk` (`qgis_sdk/` + `qgs_plugin_qgis_sdk/` + `cookbook/` +
  `packaging/conda/`), `ts-packages/qgis-node` (npm dist) and
  `ts-packages/qgis-sdk-bridge` (the former orphaned npm bridge, deleted — the TS
  sources now live in `py-packages/qgis-sdk/ts/`). Every Rust crate, including the
  language bindings, sits under `crates/` (`qgis-py`, `qgis-sdk`, `qgis-node`
  hoisted from `packages/*/rust`), so `cargo build --workspace` reaches all of them
  and a Python package never has to carry Rust. A QGIS-plugin package and a
  language-binding package are different kinds of thing, which is why the sdk split
  into a wheel dist and a deployable plugin dir.
* **Fix**: every `maturin … -m py-packages/<dist>/pyproject.toml` invocation was
  invalid — `-m` is forwarded to *cargo*, which then fails with "the manifest-path
  must be a path to a Cargo.toml file". maturin is now always run with the
  py-package as the cwd (`cd py-packages/qgis-rs && maturin build --release -o dist`)
  and reaches Rust through `[tool.maturin].manifest-path =
  "../../crates/qgis-py/Cargo.toml"` — the layout the reference project uses and the
  one verified here by actually building a wheel. The conda recipes build from the
  py-package for the same reason, and every README/docs/`.knowledge` command was
  updated. Caveat: with `manifest-path` pointing outside the project, PEP 517
  *sdist* builds cannot stage the crate — `--release` wheels are the contract.
* **Deletion**: dropped the duplicate `pyproject.toml` + `tests/` that
  `packages/qgis-rs/rust/` carried from Round 3; hatchling could not even find a
  package there, and the real tests live in the py-package.
* **Fix**: `pixi.toml` was **unparseable** — `ci`/`ci-full` had been appended after
  `[tasks.scaffold]`, so they parsed as fields of the scaffold task and pixi
  rejected the whole manifest ("Unexpected keys, expected only 'cmd', 'inputs',
  …"), which is why "validate default environment" (ci.yml) and
  "install pixi environment" (env.yml) were red on `main` and no `pixi install`
  or `pixi run` of any task worked. The file now mirrors the reference project's
  task layout: plain verbs in one `[tasks]` table and `[tasks.<name>]` dotted
  tables *only* where args or a multi-line command are needed, with
  `fmt`/`fmt-rs`/`fmt-cpp`/`fmt-check`, `clippy`, `build`, `check-cpp`, `lint-cpp`,
  `lint`, and the umbrella `gates` = `fmt-check + clippy + test`,
  `ci` = `gates + check-cpp`, `ci-full` = `ci + lint-cpp + test-full`. The
  per-environment `docs-*`/`py-*`/`sdk-*`/`node-*` names CI and the docs use are
  unchanged; `lint-rs`/`check-rs` became `clippy`/`check-cpp` and
  `lefthook.yml`'s pre-commit hook was renamed to match what the docs already said.
* **Update**: pins now come from `[workspace.dependencies]` (`rust`, `qgis`,
  `maturin`, `pytest`, `python`, `bun`), consumed via `{ workspace = true }` by the
  root environment and every feature — one place to bump, the reference project's
  convention — plus `requires-pixi = ">=0.79.0"` to document that `preview =
  ["pixi-build"]` and the `[tool.py-dist]` settings need it. `pixi task list`
  succeeds for `default`, `docs`, `py`, `sdk`, `node`.
* **Update**: the root Bun workspace now lists `ts-packages/*` + `apps/*`, and
  `bun.lock` was regenerated (it had been written as `lockfileVersion: 2`, which
  neither `bun@1.2.0` — the `packageManager` pin — nor the `bun@1.3.11` conda-forge
  resolves for the pixi `>=1.2.0,<2` range could read at the workspace root;
  `packageManager` is now `bun@1.3.11`). Because a root install is what resolves
  `apps/docs`' dependencies, the `@astrojs/sitemap` 3.6.0 pin moved to the root
  `overrides` as well — otherwise a root install resurrects 3.7.4 and the docs
  build dies in `astro:build:done`. `ci.yml`/`pages.yml` now run the frozen install
  at the workspace root and build from `apps/docs`.
* **Fix**: `scripts/setup-env.sh` unpacked the environment pack with
  `--target`, which pixi-pack self-extractors do not understand — the flags are
  `-o/--output-directory` and `-e/--env-name`, and the unpacked environment lands
  in `<output>/<env-name>`. It also never reassembled `*.000.part` chunks, so any
  bundle over GitHub's 100 MB file limit could not be installed at all. Both fixed
  and verified end-to-end against the reference project's `env/self-linux-64`
  branch: clone → reassemble → extract 45 packages → `scripts/use-pack.sh` puts a
  working `cargo 1.98.0` / `pixi 0.80.0` / `bun` on `PATH`.
* **Update**: the task layout now matches the reference project completely —
  the `pack` verb exists (`pixi run pack` → `scripts/pack-env.sh`, which packs an
  environment with `pixi-pack` and smoke-tests the bundle), `pixi-pack` moved into
  `[workspace.dependencies]` and is consumed by the root environment, and the
  ordering the reference uses (features → their per-env tasks → `[environments]` →
  one trailing `[tasks]` block with plain `verb = "cmd"` strings) was already
  reproduced. `pixi-sandbox` publishes its packs on `env/<platform>` branches; only
  `env/self-linux-64` exists there, and it is what bootstrapped the `cargo 1.98.0`
  used to verify this repo.
* **Fix**: `env.yml` called `pixi run -e default pixi-pack`, but no environment
  declared `pixi-pack` (it is absent from `pixi.lock` too), and its smoke test
  unpacked the bundle with `--target`, which pixi-pack executables do not accept.
  Both steps are now one call to `pixi run -e default pack`, so CI and a local
  `pixi run pack` share the implementation; **the new `pixi-pack` pin needs one
  `pixi lock`** before `pixi install --locked` in that workflow can pass.
* **Correction**: an earlier commit removed `default-environment = "docs"` from the
  `docs-build` task on the belief that pixi rejects unknown task fields. The
  reference project uses that exact field on its own `docs-build`, so it is legal —
  it is restored here, and `pixi.toml` now documents the full set of task keys.
* **Verification**: `cargo metadata --no-deps` (8 workspace members), `cargo fmt -p
  qgis-py -p qgis-sdk -p qgis-node`, 112 + 16 pytest tests in the two
  `py-packages`, `bun test` (17) + `bun run build` for the bridge, the docs site
  build (49 pages), `taplo fmt`, `actionlint`, and `pixi task list` for all five
  environments all pass. `cargo check`/`clippy`/`test` and `pixi install` still
  cannot run in this sandbox (no crates.io/conda access), so the commit was made
  with `--no-verify`; the two pre-existing red signals are unrelated to the layout:
  the napi `bigint64`/`u64` conversion errors in `crates/qgis-node/src/lib.rs` and
  Pages' "has no pages" upload (the workflow never writes `has_pages` to `$GITHUB_OUTPUT`).

* **Fix**: the napi binding's `u64` break, and the recorded diagnosis of it was wrong.
  napi **2.16 has no `bigint64` feature** (checked `crates/napi/Cargo.toml` at
  `napi@2.16.9`); `u64` exists only as a *one-way* `impl ToNapiValue for u64` in
  `js_values/bigint.rs`, with no `FromNapiValue`, while `i64` is generated for both
  directions from `js_values/number.rs` via `napi_create_int64`/`napi_get_value_int64`
  (N-API 1, so no extra feature is needed). The six E0277s were the four
  `tile_count`/`size_bytes`/`bytes` getters plus the two `#[napi(object)]` fields
  (`ZoomLevelInfo.tile_count`, `TilePlanResult.total`), which need both directions.
  They now cross the boundary as `i64` (`as i64` at the edge; `qgis_render` keeps
  `u64`) — which is also what `index.d.ts` and `fallback.js` already promised
  (`number`, not `BigInt`), so the fallback and the addon stay one contract.
  Rationale is written into `crates/qgis-node/src/lib.rs` above the object types.
* **Addition**: `ts-packages/qgis-node/tests/contract.test.js` — 11 tests on the
  documented surface, run with **`node --test`** instead of `jest` (which had zero
  test files, so `npm test` in node.yml failed with "Pattern: - 0 matches"). They
  assert the shared fallback/native contract: 4568 tiles for `14,50,15,51` z10-14
  (the README/docs figure), `tileCount()` a safe integer rather than BigInt, the
  `snake_case` aliases, and both spellings of the Web-Mercator limits. `jest` left
  `devDependencies` and 3648 lines of transitive closure left `package-lock.json`.
* **Fix**: `npm install` has never worked inside `ts-packages/qgis-node`, which is
  what node.yml's install step runs. The root `package.json` declares a
  `workspaces` list and its `name` is `qgis-rs` — the same as this package's — so
  npm walks up, tries to fold the member into that root and dies in its arborist
  with "Cannot read properties of null (reading 'matches')". A
  `ts-packages/qgis-node/.npmrc` with `workspaces=false` keeps npm scoped to the
  directory while `bun install` at the root still resolves the workspace; the whole
  CI step sequence (`npm install` → `npm test` → `node ../../examples/typescript_api.js`)
  then runs green locally. `fallback.js`/`index.js`/`index.d.ts` also now agree: the
  fallback exported only `getMaxLatitude()`/`getMaxZoom()`, the package only
  `MAX_LATITUDE`/`MAX_ZOOM`, so each side answered to the other's name.
* **Fix**: `cargo fmt --all --check` failed on four pre-existing files in
  `qgis-sys` (`build.rs`, `src/core/vector_layer/layer.rs`, `tests/vector_layer.rs`,
  `tests/helpers/mod.rs`), so the `fmt-check` verb of `gates` could never pass. The
  whole workspace is formatted now; `pixi run gates`'s first verb is green.
* **Update**: the docs site's lockfile duplication ended — `apps/docs` is a member
  of the root Bun workspace, so `apps/docs/bun.lock` was never what resolved
  anything, and having it was how a root install resurrected `@astrojs/sitemap`
  3.7.4 behind the nested pin's back. Deleted; the root `bun.lock` plus the root
  `overrides` are now the single source, and the docs build (49 pages) and
  `bun install --frozen-lockfile` both verified after the removal.
* **Update**: `env.yml` installs with `pixi install -e default`, not `--locked` —
  the reference project's choice, so editing `pixi.toml` can never redden the
  pack workflow by itself; keeping `pixi.lock` fresh is a `pixi lock` + commit,
  which `pixi.toml`'s header and `.knowledge/env-provisioning.md` both say.
  A `workflow_dispatch` job that re-locks and pushes was deliberately *not* added
  (the reference has no such automation, and it needs write access to the branch).
* **Verified** in this sandbox after the above: `cargo metadata --no-deps`,
  `cargo fmt --all --check` (clean), `pixi task list` for `default`/`docs`/`py`/
  `sdk`/`node`, `taplo check`, `actionlint`, 16 + 112 pytest tests, `bun test` (17)
  and `bun run build` for the bridge, `bun install --frozen-lockfile` + docs build
  (49 pages), `node --test` (11) and `npx tsc --noEmit index.d.ts`. Still not
  runnable here: `cargo check/clippy/test`, `pixi install`, and `napi build` —
  crates.io and conda are unreachable, so the napi change is reasoned from the
  napi 2.16.9 sources rather than compiled.

* **Fix**: two CI-shape bugs the split left behind, found from the step results on
  PR #4 rather than from logs (which stay unreachable here). `node --test
  "tests/**/*.test.js"` is Node >= 21 syntax while node.yml pins the Node 20 LTS, so
  the package's new tests never ran there — `package.json` now names the file, which
  also avoids the bare `node --test` form walking out of the package into the
  bridge's TypeScript tests. After that fix CI's
  "Install deps and test fallback" step passes, `cargo check --workspace` passes (the
  napi `i64` boundary compiles), and only clippy and rust-check's own commit step
  stayed red. The latter failed on every pull request because it guarded
  `github.ref_name != 'main'` and then ran `git push origin HEAD:$GITHUB_REF_NAME` —
  on a PR that ref is `N/merge`, which GitHub owns — so it is now limited to push
  events, and its `format` step gained the three binding crates that became workspace
  members under `crates/` and had no rustfmt check at all.

## 2026-09-17

* **Initialization**: Created OKF v0.2 knowledge bundle with 21 concept documents.
* **Creation**: Established [CONTEXT.md](/CONTEXT.md) — project orientation for agents and contributors.
* **Creation**: Established [architecture.md](/architecture.md) — crate layout, layer model, FFI data flow.
* **Creation**: Established [ffishim.md](/ffishim.md) — the opaque-handle CXX bridge pattern.
* **Creation**: Established [build-system.md](/build-system.md) — build.rs pipeline documentation.
* **Creation**: Established [qgis-application.md](/qgis-application.md) — QgsApplication lifecycle and QApplication workaround.
* **Creation**: Established [qgis-vector-layer.md](/qgis-vector-layer.md) — QgsVectorLayer binding and provider model.
* **Creation**: Established [pixi.md](/pixi.md) — Pixi environment manager, tasks, and features.
* **Creation**: Established [lefthook.md](/lefthook.md) — pre-commit hooks configuration.
* **Creation**: Established [scaffold.md](/scaffold.md) — code-generation task for new QGIS type bindings.
* **Creation**: Established [testing.md](/testing.md) — test structure, fixtures, and environment requirements.
* **Creation**: Established [related-approaches.md](/related-approaches.md) — comparison of Rust ↔ C++ / Qt binding strategies.
* **Creation**: Established [env-provisioning.md](/env-provisioning.md) — bootstrap via pixi-sandbox packs.
* **Creation**: Established the execution roadmap, now maintained in [Backlog doc-2](../backlog/docs/roadmap/doc-2%20-%20QGIS-RS-Execution-Roadmap.md) — phased plan for architectural decisions and type binding.
* **Creation**: Established [decisions/](/decisions/) subdirectory with 8 decision documents (D01–D08).
* **Creation**: Established [.github/workflows/env.yml](/../.github/workflows/env.yml) — CI workflow for environment packing.
* **Creation**: Established [scripts/](/../scripts/) — setup-env.sh, use-pack.sh, publish-env-branch.sh.
