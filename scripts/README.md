# scripts/

Every task longer than one line lives here as a POSIX-ish bash script, and the
manifests (`pixi.toml`, `*/package.json`, `.github/workflows/*.yml`) only *call*
them. That rule exists because a multi-line command embedded in TOML or JSON is
unreviewable, un-lintable, un-runnable outside its manifest, and silently
diverges between the local gate and CI.

Contract for every script in this directory:

* `#!/usr/bin/env bash` + `set -euo pipefail`.
* Runnable from any working directory — each one `cd`s to the repository root
  itself (`REPO_ROOT`), so `bash scripts/x.sh` and a pixi task agree.
* No pixi *environment* assumptions inside the script unless its name says so:
  scripts named `*-in-env.sh` assume they already run under `pixi run -e …`;
  the rest re-enter pixi explicitly.
* Arguments are optional refinements (staged files, extra pytest flags), never
  required configuration.

| Script | Called by | What it does |
| --- | --- | --- |
| `ci.sh` | `pixi run ci`, CI workflow | The whole gate: repo lints, turbo lint, format-drift gate, tests, `pack:check`, coverage |
| `check-cpp.sh` | lefthook, `pixi run check-cpp` | `clang-format --dry-run --Werror` on staged files or the whole C++ tree |
| `lint-toml.sh` | lefthook, `pixi run lint-toml` | `taplo fmt --check` on staged manifests or the two canonical ones |
| `scaffold.sh` | `pixi run scaffold` | Generates a qgis-sys header / bridge / shim triple |
| `rust-build.sh` | `@qgis/rust` `build` | `cargo build --release` under the QGIS env |
| `rust-test.sh` | `@qgis/rust` `test`, `test:full` | Headless (`--fast`) or QGIS-backed Rust suites |
| `rust-lint.sh` | `@qgis/rust` `lint` | `cargo fmt --check`, clang-format, clippy, clang-tidy |
| `rust-format.sh` | `@qgis/rust` `format`, `format:cpp` | `cargo fmt` and/or `clang-format -i` |
| `rust-coverage.sh` | `@qgis/rust` `coverage` | `cargo llvm-cov` → `target/coverage/rust-lcov.info` |
| `py-build.sh` | `qgis-*-py` `build` | `maturin develop` **and** `maturin build --release -o dist` in one step |
| `py-test.sh` | `qgis-*-py` `test` | Ensures the extension is installed, then pytest |
| `py-coverage.sh` | `qgis-*-py` `coverage` | pytest with `--cov` → `target/coverage/python-<dist>.xml` |
| `npm-pack-check.sh` | `qgis-rs` (npm) `pack:check` | Asserts every file the package claims to ship exists |
| `version.ts` | `pixi run version[-check\|-set]` | The single source of truth for the release version |
| `release/*.sh` | `release.yml` | Version verification, artifact builds, checksums, registry uploads |
