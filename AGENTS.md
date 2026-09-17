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

The `.knowledge/` directory contains design documents, decision records, and architectural information:

- **INDEX.md** — Entry point to all knowledge documents
- **architecture.md** — System architecture and component overview
- **ROADMAP.md** — Development roadmap and priorities
- **decisions/** — Architecture Decision Records (D01-D08)
- **api-design.md** — Public API specification
- **qgis-plugin-sdk.md** — Plugin framework design

**Always consult the knowledge base before making architectural decisions.**

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

- All C++ ↔ Rust communication goes through CXX bridges
- Use `#[cxx::bridge]` modules in `.rs` files
- Declare C++ types as opaque handles
- Convert strings at the boundary (QString ↔ Rust String)
- Never expose Qt types to Rust (convert to primitives)

## Testing

### Test Structure

```
tests/
├── application_info.rs      # Basic QGIS initialization
├── application_lifecycle.rs # RAII patterns, cleanup
└── vector_layer.rs          # Layer operations
```

### Running Tests

```bash
# Basic tests (no QGIS data needed)
pixi run test

# Full tests (requires QGIS environment)
pixi run test-full

# Specific package
pixi run test qgis-sys
```

### Test Requirements

- All tests must set `QT_QPA_PLATFORM=offscreen` for headless execution
- Use `--test-threads=1` to avoid Qt threading issues
- Tests should be idempotent and not modify shared state
- Prefer unit tests over integration tests when possible

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

1. Run `pixi run fmt` to format code
2. Run `pixi run lint` to check for issues
3. Run `pixi run test` to ensure tests pass
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
