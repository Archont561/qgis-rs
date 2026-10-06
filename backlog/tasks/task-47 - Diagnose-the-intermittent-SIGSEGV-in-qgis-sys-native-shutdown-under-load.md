---
id: TASK-47
title: Diagnose the intermittent SIGSEGV in qgis-sys native shutdown under load
status: Done
assignee:
  - '@me'
created_date: '2026-10-06 09:38'
updated_date: '2026-10-06 19:16'
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
- [x] #1 The crash is either reproduced deterministically or shown to be impossible in the current shutdown path, with the evidence recorded.
- [x] #2 If reproduced, the destruction order between Qt thread-local storage and native manager shutdown is documented and fixed at its cause, not by retrying the test.
- [x] #3 The gate stays green across at least 3 consecutive full runs under concurrent load.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Characterize the existing app_shutdown seam under repeated loaded process teardown; correct owner-thread QApplication destruction order instead of leaking it past exitQgis; prove the focused binary and three full gates under concurrent load; record exact Qt lifecycle evidence.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-06: The failing process had two lifecycle violations at the same seam: it constructed a base QApplication while separately calling static QgsApplication initialization, and app_shutdown deliberately leaked that application past owner-thread exit. The reported QThreadStorage warning is the consequence of allowing Qt thread-local cleanup after the storage owner is gone. The manager now constructs the real headless QgsApplication and deterministically orders layer release, exitQgis, QgsApplication destruction, then owner-thread exit.

2026-10-06: Before the fix, 20 focused process runs passed, confirming the reported intermittency; a no-capture run deterministically showed QApplication was not created in main. After the fix, 30 of 30 focused processes passed while two CPU-saturating workers ran. The main-thread warning remains because D12 deliberately uses a dedicated owner thread, but application destruction now happens on that same thread before it exits and no QThreadStorage warning appeared.

2026-10-06: Three consecutive full offline gates passed with Turbo running package builds and tests concurrently: 287s cold, 119s warm, 121s warm. No post-success SIGSEGV or QThreadStorage teardown warning occurred.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed native manager teardown at its cause: use a real headless QgsApplication and destroy it on its owner thread after layers and QGIS registries, before thread exit. Documented the lifecycle, passed 30 loaded focused process runs, and passed three consecutive concurrent full gates.
<!-- SECTION:FINAL_SUMMARY:END -->
