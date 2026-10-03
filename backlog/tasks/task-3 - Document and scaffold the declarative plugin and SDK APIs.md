---
id: task-3
title: Document and scaffold the declarative plugin and SDK APIs
status: To Do
assignee: []
created_date: '2026-09-30'
updated_date: '2026-10-03 08:31'
labels:
  - qgis-sdk
  - documentation
  - scaffold
milestone: m-3
dependencies: []
documentation:
  - .knowledge/qgis-plugin-sdk.md
  - .knowledge/qgis-plugin-ui.md
  - .knowledge/scaffold.md
priority: medium
---

## Description

The SDK now supports declarative plugins, algorithms, decorated network clients, retries, and fluent tasks, but the public documentation and generated plugin templates do not yet provide a complete path for using these APIs. Make the new surface discoverable and ensure scaffolded plugins exercise the supported lifecycle.

## Acceptance Criteria

- [ ] The SDK guide documents standalone `@plugin` usage, `@algorithm` registration, and compatibility with the `Plugin` base class.
- [ ] Network documentation covers `@session`, `http.get`/`post` endpoint decorators, direct requests-like functions, and retry policy configuration.
- [ ] Task documentation covers signatures, chains, groups, `.delay()`, `.apply_async()`, and fallback behavior.
- [ ] The scaffold can generate a minimal declarative plugin with an action and Processing algorithm.
- [ ] Generated plugin tests use the reusable runtime fixtures and include a pure-Python path.
- [ ] Documentation examples are covered by focused tests or a fixture-backed smoke test.

## Definition of Done

- [ ] README/docs pages and scaffold templates agree with the exported APIs.
- [ ] A new plugin developer can generate and run the minimal example without manually wiring registry internals.
- [ ] Backward-compatible `Plugin` examples remain documented.
