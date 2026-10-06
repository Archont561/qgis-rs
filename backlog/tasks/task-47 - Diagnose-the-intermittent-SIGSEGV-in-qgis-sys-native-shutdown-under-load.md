---
id: TASK-47
title: Diagnose the intermittent SIGSEGV in qgis-sys native shutdown under load
status: To Do
assignee: []
created_date: '2026-10-06 09:38'
updated_date: '2026-10-06 09:38'
labels:
  - testing
  - qgis-sys
  - flake
dependencies: []
priority: medium
type: bug
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
During the session 7 full gate run, qgis-sys::native_manager_shutdown shutdown_releases_layers_left_open_on_the_owner_thread aborted with SIGSEGV while a concurrent turbo task (maturin --release) saturated the CPU. It did not reproduce: 5 isolated runs, 3 whole-crate runs and 3 runs of the exact gate command all passed, and the gate re-run was green. So this is an intermittent native-teardown fault that only appears under load, not a deterministic failure. The preceding stderr was "QThreadStorage: Thread exited after QThreadStorage 5 destroyed", which points at destruction ordering between Qt thread-local storage and the manager shutdown path rather than at the test. Worth diagnosing before it costs someone a red CI run they cannot reproduce.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The crash is either reproduced deterministically or shown to be impossible in the current shutdown path, with the evidence recorded.
- [ ] #2 If reproduced, the destruction order between Qt thread-local storage and native manager shutdown is documented and fixed at its cause, not by retrying the test.
- [ ] #3 The gate stays green across at least 3 consecutive full runs under concurrent load.
<!-- AC:END -->
