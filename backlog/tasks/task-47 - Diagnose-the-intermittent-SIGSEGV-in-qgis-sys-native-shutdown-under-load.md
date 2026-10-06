---
id: TASK-47
title: Diagnose the intermittent SIGSEGV in qgis-sys native shutdown under load
status: To Do
assignee: []
created_date: '2026-10-06 09:38'
updated_date: '2026-10-06 09:41'
labels:
  - testing
  - qgis-sys
  - flake
  - native
dependencies: []
priority: medium
type: bug
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Seen in two independent sessions, which is why it is filed rather than dismissed as noise. Session 7 hit it during one of its two closing gate runs; session 8 hit it during a full gate run while a concurrent turbo task (maturin --release) saturated the CPU. Both times nextest printed the test as passing and the process then aborted with signal 11 during teardown, preceded by "QThreadStorage: Thread exited after QThreadStorage 5 destroyed" and "QApplication was not created in the main() thread". Both times the identical tree was green on a re-run; session 8 failed to reproduce it in 11 further targeted runs (5 isolated, 3 whole-crate, 3 of the exact gate command). So the fault is in Qt/QGIS process teardown, not in the test body, and it surfaces under load. Session 7 suggested this belonged to TASK-35, but TASK-35 owns QgsApplication lifecycle in the Python SDK, whereas this crash is in the Rust qgis-sys native manager shutdown path - a different layer, hence a separate task. A test binary that can abort after reporting success will redden CI at random, and the person who sees it will not be able to reproduce it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The crash is either reproduced deterministically or shown to be impossible in the current shutdown path, with the evidence recorded.
- [ ] #2 If reproduced, the destruction order between Qt thread-local storage and native manager shutdown is documented and fixed at its cause, not by retrying the test.
- [ ] #3 The gate stays green across at least 3 consecutive full runs under concurrent load.
<!-- AC:END -->
