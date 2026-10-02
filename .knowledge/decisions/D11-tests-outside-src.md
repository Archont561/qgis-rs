---
type: Decision
id: D11
title: Tests Live in `tests/`, Never Inside `src/`
description: "One layout in every language: source in src/, tests in tests/, and anything a test needs is public."
status: accepted
tags: [testing, layout, rust, conventions]
date: 2026-10-03T00:00:00Z
---

# D11: Tests Live in `tests/`, Never Inside `src/`

## The Question

Rust's default is to put unit tests in the file they test, behind
`#[cfg(test)] mod tests`. This repository had ~1100 lines of them across 21
files, while the Python distributions, the npm packages and the `qgis-sys`
integration suite all kept tests in a `tests/` directory next to the sources.

Two layouts, two answers to "where are the tests for this?", and a reader of
`crates/qgis-render/src/tiles.rs` had to scroll past a third of a file of
assertions to find the next function.

## The Decision

**`src/` holds code. `tests/` holds tests. Everywhere.**

| Tree | Source | Tests |
| --- | --- | --- |
| Rust crate | `crates/<crate>/src/` | `crates/<crate>/tests/<topic>.rs` |
| Python distribution | `py-packages/<dist>/{src,python}/` | `py-packages/<dist>/tests/` |
| npm package | `ts-packages/<pkg>/src/` | `ts-packages/<pkg>/tests/` |
| C++ shim | `crates/qgis-sys/src/`, `include/` | `crates/qgis-sys/tests/` |

No `#[cfg(test)]` module survives in `src/`; `cargo test` finds the same 120
tests it did before, as integration tests. `ts-packages/qgis-node` — the one
package whose sources sat at its root — moved `index.js` / `index.d.ts` into
`src/`, so `main`, `files` and `pack:check` name a directory rather than a
list of loose files.

### What follows from it

* **A test is a consumer.** An integration test links the crate from outside,
  so it reaches exactly what any other caller reaches. Where a test needed a
  private item, that item became `pub` with a doc comment saying so: `xtask`'s
  `CRATES` and `already_published`, `qgis-cli`'s `split_list` and
  `what_is_served`, `qgis-mcp`'s `#[tool]` handlers and a public `tools()`
  accessor for the router the macro generates privately.
* **A binary-only crate needs a library.** `crates/xtask` is now `src/lib.rs`
  plus a six-line `src/main.rs`, because `tests/` cannot link a `[[bin]]`.
* **The binding crates get a test each.** `crates/qgis-py/tests/adapter.rs`
  and `crates/qgis-node/tests/adapter.rs` assert the one thing those crates
  do: carry the request to the engine unchanged.

## Why

* **One place to look, in every language.** "Where are the tests for X" has a
  single answer across a repository that already asks a contributor to move
  between Rust, Python, TypeScript and C++.
* **Testing the surface, not the inside.** A unit test that reaches a private
  function tends to pin down *how* something works; the same test written from
  outside pins down *what* it does. The handful of items this change made
  public were, in each case, either genuinely part of the crate's contract (the
  MCP tool handlers) or a list that exists to be checked (the publish order).
* **Diffs that read.** A behaviour change and its test no longer land in the
  same file, so a reviewer sees "this changed, and here is the assertion that
  now covers it" instead of one blob.
* **It makes the next step possible.** Property-based testing (proptest,
  Hypothesis, RapidCheck) and fixture libraries (rstest, pytest fixtures,
  GoogleTest) are organised per *suite*, not per source file; a `tests/` tree
  is where that generation belongs. Tracked in the backlog.

## The Costs, Accepted

* **Private helpers can no longer be tested directly.** Accepted: that is the
  point. Where it would have forced an unnatural `pub`, the test was pointed at
  the public behaviour that exercises the same code instead.
* **Compile time.** Each `tests/*.rs` is its own binary, so 21 new link steps.
  Measured at a few seconds on a warm workspace, against test binaries that are
  now independent and can run in parallel.
* **`pub` on items nothing else calls.** Each one carries a doc comment that
  says the test is the caller, and every such crate is either `publish = false`
  or already exposes that surface conceptually.

## Alternatives Considered

| Alternative | Why not |
| --- | --- |
| Keep Rust idiomatic (`#[cfg(test)]` in `src/`), split only the other languages | Preserves the two-layouts problem the change exists to remove, and leaves `src/tiles.rs` a third assertions |
| Move the tests into `src/tests/` submodules | Still inside `src/`, still compiled as part of the crate, and now the file says `#[path]` games instead of saying what it tests |
| Leave the private-item tests inline and move only the rest | A rule with exceptions is not a rule a reviewer can apply; the exceptions were also exactly the tests worth rewriting from outside |

## Consequences

* 21 test modules became 22 files under `crates/*/tests/`, each with a header
  saying what it covers; `crates/qgis-node/tests/adapter.rs` is new.
* `crates/xtask` gained `src/lib.rs`; `src/main.rs` is six lines.
* `ts-packages/qgis-node` gained `src/`, and its `package.json` `main`,
  `types`, `files` and `pack:check` entries were updated with it.
* `AGENTS.md` states the convention for future work.
