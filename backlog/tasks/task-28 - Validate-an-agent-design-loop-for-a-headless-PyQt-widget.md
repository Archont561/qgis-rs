---
id: TASK-28
title: Validate an agent design loop for a headless PyQt widget
status: Done
assignee: []
created_date: '2026-10-03 08:50'
updated_date: '2026-10-08 22:30'
labels:
  - qgis-sdk
  - ui
  - agent
  - visual-testing
milestone: m-3
dependencies: []
documentation:
  - .knowledge/qgis-ui-agent-design-loop.md
  - >-
    backlog/docs/ui/doc-9 -
    Agent-Driven-PyQt-QGIS-Visual-Design-Loop-Spec.md
modified_files:
  - >-
    backlog/docs/ui/doc-9 -
    Agent-Driven-PyQt-QGIS-Visual-Design-Loop-Spec.md
priority: medium
type: spike
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Test whether a bounded agent design loop can render one PyQt widget, capture its own screenshot, analyze the image, and improve a JSON design specification. Compare the reusable loop shape with Archont561/archont561 HTML/CSS/JS screenshot automation, while keeping the Qt/QGIS lifecycle and visual/behavior boundaries explicit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A real custom-painted QWidget runs with QT_QPA_PLATFORM=offscreen and captures a PNG through QWidget.grab().
- [x] #2 The loop writes per-iteration design and image-analysis JSON, keeps screenshot history, and stops at a bounded iteration count.
- [x] #3 A deterministic reviewer improves the intentionally weak initial design without requiring model credentials.
- [x] #4 An external reviewer command seam receives the screenshot path and metrics and returns a schema-validated complete DesignSpec.
- [x] #5 The feasibility result, QGIS adaptation seam, environment limitation, and safety constraints are documented in the knowledge base.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Validation: python tools/pyqt-design-loop/test_design_loop.py (4 tests passed).

Validation: real PyQt5 offscreen run produced iteration-00.png (520x300) and iteration-01.png (720x420), with score 0.5330 -> 1.0000.

Validation: temporary reviewer command received stdin JSON and returned a complete DesignSpec; final title was accepted.

Limitation: base shell lacks Pixi, Qt, and libGL.so.1. The runtime probe used temporary PyQt5 and an offscreen OpenGL stub outside the repository; QGIS integration remains TASK-29.

2026-10-08: the probe tooling was removed from the repository (`tools/pyqt-design-loop/` deleted) so the design loop is no longer shipped as repo tooling. The validated loop design moved to the backlog specification `backlog/docs/ui/doc-9 - Agent-Driven-PyQt-QGIS-Visual-Design-Loop-Spec.md`; the evidence above and in the knowledge entry is retained. TASK-29 builds the loop per that spec against a real QGIS widget.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Feasibility confirmed. The real PyQt5 probe ran headlessly for two iterations, captured valid 520x300 and 720x420 PNGs, and improved the deterministic score from 0.5330 to 1.0000. The probe implementation was later removed from the repository; the validated design is specified in backlog doc-9, and QGIS integration remains a follow-up (TASK-29).
<!-- SECTION:FINAL_SUMMARY:END -->
