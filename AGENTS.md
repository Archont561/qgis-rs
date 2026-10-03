# AI Agent Guidelines

This document provides guidelines for AI agents (like Claude, GPT-4, Copilot, etc.) working on the qgis-rs codebase.

## Project Context

**qgis-rs** provides safe Rust bindings to the QGIS C++ API using CXX. The project uses:

- **Rust 1.96+** with edition 2021
- **CXX** for safe C++ FFI (not bindgen or manual FFI)
- **Pixi** for dependency management (conda-forge)
- **QGIS 3.44.9+** as the target API
- **OKF v0.2** for knowledge base documents

## Knowledge Base

Before implementing a feature or fixing a bug, read both `.agents/skills/refactor/SKILL.md` and `.agents/skills/tdd/SKILL.md`. Apply the relevant guidance: establish the public seam and a failing characterization or behavior test first, make one small behavior-preserving change at a time, run the focused tests, then refactor only after the test is green.

The `.knowledge/` directory contains design documents, decision records, and architectural information:

- **INDEX.md** — Entry point to all knowledge documents
- **architecture.md** — System architecture and component overview
- **ROADMAP.md** — Development roadmap and priorities
- **decisions/** — Architecture Decision Records (D01-D11)
- **api-design.md** — Public API specification
- **qgis-plugin-sdk.md** — Plugin framework design

**Always consult the knowledge base before making architectural decisions.**

## Agent Tooling

The repository carries the same agent workflow used by `pixi-sandbox`:

- Skills are versioned under `.agents/skills/` and their provenance is recorded in `skills-lock.json`.
- Install the root Bun workspace with `pixi run bun-install`.
- Run the skills CLI with `pixi run skills` (equivalent to `bun x skills`).
- Manage project work as Markdown tasks with `pixi run backlog` (equivalent to `bun x backlog`).
- Read backlog output non-interactively, for example `pixi run backlog task list --plain`.

Do not hand-edit backlog task metadata when the CLI can make the change; use the backlog skill's
workflow so IDs, dependencies, acceptance criteria, and status remain consistent.

## Code Style

### Rust

- Use `cargo fmt` for formatting (enforced by CI)
- Use `cargo clippy` for linting (enforced by CI)
- Follow Rust API Guidelines: https://rust-lang.github.io/api-guidelines/
- Prefer `Result<T, QgisError>` over panics
- Use builder pattern for configuration objects
- Document all public APIs with `///` doc comments

### C++

- Use `clang-format` for formatting (enforced by CI)
- Use `clang-tidy` for linting (enforced by CI)
- Follow the shim pattern: thin wrappers around QGIS classes
- Use opaque handles for QGIS objects
- Namespace: `qgis_shim::{layer}::{concept}`

### FFI Boundaries

**Rust ↔ C++** (`crates/qgis-sys`):

- All C++ ↔ Rust communication goes through CXX bridges
- Use `#[cxx::bridge]` modules in `.rs` files
- Declare C++ types as opaque handles
- Convert strings at the boundary (QString ↔ Rust String)
- Never expose Qt types to Rust (convert to primitives)

**Rust ↔ Python / Node** (`crates/qgis-py`, `crates/qgis-node` — see
[D09](.knowledge/decisions/D09-wire-protocol-over-ffi.md)):

- Each binding crate exposes **one** function, `invoke(request_json) -> response_json`.
  Do not add a `#[pyclass]` or a `#[napi]` struct per domain type.
- A new capability is a variant of `Operation` in `crates/qgis-protocol`, a
  payload struct and a match arm in `crates/qgis-engine` — plus a test in
  `crates/qgis-engine/tests/engine.rs`, which is where the boundary is covered.
- Everything on the wire is `snake_case`, including operation names. The
  JavaScript client renames to camelCase at its own edge; Python does not rename.
- The ergonomic classes live in the host languages
  (`py-packages/qgis-rs/python/qgis_rs/_api.py`, `ts-packages/qgis-node/src/index.js`),
  never in the binding crates. There are no pure-Python or pure-JS fallbacks.

### Repository automation

Repository-wide automation is `crates/xtask`, not shell
([D10](.knowledge/decisions/D10-xtask-over-shell-scripts.md)). Add a subcommand
there — with a unit test — rather than a `scripts/*.sh`; `pixi run xtask <sub>`
reaches it without a new pixi task. Per-package verbs (`build`, `test`, `lint`,
`format`, `coverage`, `pack:check`) stay in the package's own `package.json`,
are fanned out by turbo, and are **one line each** — `pixi run` keeps the
package directory as the working directory, so a package verb needs no `cd` and
no wrapper script.

Source has to be visible to git. `.gitignore` ignores `.*` and `_*`, which once
swallowed the whole Python client (`_api.py`, `_transport.py`) without a word
from `git status`; `pixi run xtask check-sources` now fails the gate when a
file under `crates/`, `py-packages/`, `ts-packages/` or `scripts/` looks like
source and is ignored.

## Testing

### Test Structure

**`src/` holds code, `tests/` holds tests — in every crate and every package.**
There are no `#[cfg(test)] mod tests` blocks in `src/`; a Rust test is an
integration test in `crates/<crate>/tests/<topic>.rs` that uses the crate the
way any other consumer would. The same split already holds for the Python
distributions (`py-packages/*/tests/`) and the npm packages
(`ts-packages/*/tests/`). See
[D11](.knowledge/decisions/D11-tests-outside-src.md).

Two consequences worth knowing before you write one:

- If a test needs an item, that item is **public**, with a doc comment saying
  the test is why. If making it public feels wrong, the test is usually
  asserting an implementation detail rather than a behaviour.
- A crate that is only a binary needs a library to be testable, so
  `crates/xtask` is `src/lib.rs` plus a six-line `src/main.rs`.

```
crates/qgis-sys/tests/
├── application_info.rs      # Basic QGIS initialization
├── application_lifecycle.rs # RAII patterns, cleanup
└── vector_layer.rs          # Layer operations
```

### Running Tests

Packages own their test scripts; run them repo-wide or scoped via turbo.

```bash
# Everything (Rust workspaces, Python packages, napi FFI, bridge)
bun x turbo run test

# Rust workspace only — the @qgis/rust façade chains both suites:
# application_info first (no QGIS data), then the full lifecycle/vector tests
bun x turbo run test --filter=@qgis/rust

# Python plugin SDK alone (runs without QGIS)
bun x turbo run test --filter=qgis-sdk
```

### Test Requirements

- All tests must set `QT_QPA_PLATFORM=offscreen` for headless execution
- Use `--test-threads=1` to avoid Qt threading issues
- Tests should be idempotent and not modify shared state
- Name a test after the behaviour it pins down, not the function it calls

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`

**Scopes**: `qgis-sys`, `render`, `cli`, `server`, `sdk`, `docs`, `ci`

**Examples**:
- `feat(qgis-sys): add QgsGeometry bindings`
- `fix(render): correct extent calculation for rotated maps`
- `docs: update API reference for Project::open`

Enforced by `lefthook` pre-commit hooks.

## Pull Requests

### Before Opening a PR

1. Run `bun x turbo run format` to format code
2. Run `bun x turbo run lint` to check for issues
3. Run `bun x turbo run test` to ensure tests pass
4. Update documentation if changing public APIs
5. Add tests for new functionality

### PR Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Commit messages follow conventional commits
- [ ] No breaking changes (or documented in CHANGELOG)

## Common Pitfalls

### Thread Safety

QGIS is **not thread-safe**. Never:
- Share QGIS objects across threads
- Call QGIS functions from multiple threads simultaneously
- Use `Send` or `Sync` traits on QGIS wrappers

Instead:
- Use a single-threaded event loop
- Clone data before passing to worker threads
- Use message passing for cross-thread communication

### Memory Management

- QGIS objects use reference counting internally
- Rust wrappers should use RAII (Resource Acquisition Is Initialization)
- Never manually delete QGIS objects — let Rust's `Drop` handle it
- Be careful with borrowed references — QGIS may invalidate them

### Qt Integration

- QGIS requires a `QApplication` instance
- Use the `QgsApplication` wrapper which handles initialization
- Set `QT_QPA_PLATFORM=offscreen` for headless operation
- Avoid Qt event loops in library code (use callbacks instead)

## Documentation

### Public APIs

All public functions, structs, and enums must have doc comments:

```rust
/// Opens a QGIS project from the specified path.
///
/// # Arguments
///
/// * `path` - Path to the `.qgs` or `.qgz` file
///
/// # Returns
///
/// A `Project` instance on success, or `QgisError` on failure.
///
/// # Example
///
/// ```
/// let project = Project::open("map.qgs")?;
/// println!("Loaded: {}", project.title());
/// ```
pub fn open(path: impl AsRef<Path>) -> Result<Self> {
    // ...
}
```

### Knowledge Base

When making architectural decisions:
1. Create a decision record in `.knowledge/decisions/`
2. Follow the template: `D{NN}-{title}.md`
3. Include: Context, Decision, Consequences
4. Update `.knowledge/decisions/INDEX.md`

## Security

- Never commit secrets, API keys, or credentials
- Validate all user input (file paths, expressions, SQL)
- Use parameterized queries for database access
- Sanitize output to prevent injection attacks
- Follow the principle of least privilege

## Performance

- Prefer lazy evaluation over eager computation
- Use iterators instead of collecting into vectors
- Avoid unnecessary clones (use references when possible)
- Profile before optimizing — don't guess
- Use `rayon` for parallel processing (with thread affinity)

## Accessibility

- Use semantic HTML in documentation
- Provide alt text for images
- Ensure color contrast meets WCAG 2.1 AA
- Test with screen readers when possible
- Use clear, simple language

## Internationalization

- Use UTF-8 encoding everywhere
- Support Unicode identifiers and strings
- Use ICU for locale-sensitive operations
- Document locale-dependent behavior
- Test with non-ASCII data

## Questions?

If you're unsure about something:
1. Check the knowledge base (`.knowledge/`)
2. Look at existing code for patterns
3. Ask in GitHub Discussions
4. Open an issue for clarification

---

**Remember**: The goal is to provide safe, idiomatic Rust bindings that feel natural to Rust developers while preserving the full power of QGIS.

<!-- BEGIN:turborepo-agent-rules -->

# This is NOT the Turborepo you know

Turborepo configuration, task behavior, and CLI commands can vary between installed versions and may differ from your training data. Resolve the `turbo` package from this file's directory or relevant workspace; in monorepos, it may not be visible from the repository root. For example, run `node -p "require.resolve('turbo/package.json')"` from a workspace that depends on `turbo`.

Read `docs/README.md` inside that installed package first, then read the relevant pages from its `docs/` directory before changing Turborepo configuration or commands. Heed deprecation notices. These bundled docs match the installed package version and are available without network access.

This block is written and re-added by `turbo` before repository-scoped commands when an AI agent is detected. In the Turborepo source repository, its template is defined in `crates/turborepo-cli/src/cli/agent_guidance.rs`. Removing the managed block while updates are enabled means a later qualifying invocation will add it again. Set `"agentGuidance": false` in the root `turbo.json` or `turbo.jsonc` to opt out; this does not remove an existing block. Keep the block committed with your work to avoid an uncommitted change on the next agent invocation.
<!-- END:turborepo-agent-rules -->
