---
type: Tool
title: Lefthook
description: Pre-commit and commit-msg hooks for formatting, linting, and conventional commits.
status: stable
tags: [lefthook, git, hooks, ci]
generated: { by: arena-agent/qgis-rs-kb-init, at: 2026-09-17T20:00:00Z }
---

# Lefthook

## Configuration (`lefthook.yml`)

Lefthook manages Git hooks to enforce code quality before commits.

### Pre-commit (parallel)

| Hook     | Glob           | Command                                          |
|----------|----------------|--------------------------------------------------|
| `fmt-rs` | `*.rs`         | `cargo fmt --all --check`                        |
| `fmt-cpp`| `*.{cpp,h}`    | `clang-format --dry-run --Werror {staged_files}` |
| `clippy` | `*.rs`         | `cargo clippy --workspace --all-targets -- -D warnings` |

All run in parallel for speed.

### Commit-msg

| Hook     | Command                              |
|----------|--------------------------------------|
| `convco` | `convco check --from-stdin < {1}`   |

Enforces [Conventional Commits](https://www.conventionalcommits.org/) format:
- `feat: add geometry binding`
- `fix: handle null pointer in vector_layer_name`
- `refactor: extract convert helpers`

## Installation

Lefthook is installed via pixi:

```bash
pixi run lefthook install
```

This creates the hook scripts in `.git/hooks/` that call lefthook.

## CI Alignment

The `gates`/`ci` tasks in `pixi.toml` run the same checks as the hooks, ensuring local
and CI parity:

```
gates = fmt-check + clippy + test
ci    = gates + check-cpp
```
