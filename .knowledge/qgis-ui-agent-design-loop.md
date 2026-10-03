---
type: Practice
title: Agent-Driven Qt and QGIS UI Design Loop
description: A headless screenshot, analysis, and bounded improvement loop for one PyQt/QGIS widget.
status: draft
tags: [qgis, ui, pyqt, qt, agent, visual-testing, headless]
generated: { by: arena-agent, at: 2026-10-03T08:52:00Z }
---

# Agent-driven Qt and QGIS UI design loop

## Feasibility result

A bounded agent design loop is feasible for a simple QGIS-style UI element without
using a desktop screenshot utility or a browser. The proof of concept lives at
`tools/pyqt-design-loop/`.

The probe creates one custom-painted `QWidget`, runs it with
`QT_QPA_PLATFORM=offscreen`, captures the widget with `QWidget.grab()`, analyzes
its `QImage`, and produces a next JSON design specification. The default reviewer
is deterministic so the loop is testable without model credentials. A reviewer
command seam accepts the PNG path and metrics and returns the next complete
`DesignSpec` JSON object; this is the insertion point for a vision-capable agent.

The sandbox proof ran the real PyQt5 widget and produced valid PNGs:

- iteration 0: 520 x 300, score `0.5330`, low contrast, cramped spacing, weak hierarchy;
- iteration 1: 720 x 420, score `1.0000`, no remaining heuristic issues.

The external-reviewer seam was also smoke-tested with a temporary command that
received the JSON payload on stdin and returned a complete spec on stdout.

The sandbox's base Python did not have Qt or `libGL.so.1`. The proof used a
temporary PyQt5 installation and a temporary offscreen OpenGL stub outside the
repository. This validates the loop mechanics and rendering seam, not QGIS
integration. The normal validation path remains the repository's restored Pixi
QGIS environment.

## Loop contract

```text
DesignSpec
    │
    ▼
widget factory ──► QApplication / QGIS Qt owner thread
    │
    ▼
QWidget.grab() ──► PNG + QImage
    │
    ├── deterministic metrics and constraint checks
    │
    ▼
reviewer (heuristic or external vision agent)
    │
    ▼
validated next DesignSpec ──► bounded next iteration
```

Keep these seams separate:

1. **Widget factory:** constructs the actual widget from a validated design model.
   The probe uses one custom-painted widget; production code can construct a
   `QDialog`, `QDockWidget`, or plugin panel.
2. **Capture:** call `show()`, process pending Qt events, and use `grab()` on the
   widget. This captures the widget in its real Qt style without requiring X11,
   Wayland, Chromium, or a full-screen desktop capture.
3. **Analysis:** calculate deterministic facts such as dimensions, sampled
   luminance/contrast, background coverage, and required-content presence. These
   checks are guardrails, not a substitute for visual judgment.
4. **Review:** a deterministic reviewer supports smoke tests. A model reviewer
   receives the screenshot path, current spec, metrics, and a visual-only
   instruction, then returns one complete spec. Validate model output before
   constructing Qt objects.
5. **History:** preserve every screenshot, spec, and analysis for comparison.
   Stop after a small iteration bound or when the spec stabilizes. Human approval
   remains required for production UI changes.

## QGIS/Qt constraints

- Prefer `qgis.PyQt` inside QGIS so the widget uses the host's Qt binding; the
  probe falls back to standalone PyQt5, PyQt6, or PySide6 for a simple app.
- Set `QT_QPA_PLATFORM=offscreen` in headless runs. Keep `QApplication` and all
  QObjects on the owning Qt thread; the repository's QGIS tests run serialized
  because application state is process-wide. See [Testing](testing.md) and
  [D05](decisions/D05-threading.md).
- A simple `QWidget` probe does not need `QgsApplication`. A QGIS plugin adapter
  must reuse the existing application/QGIS lifecycle instead of creating a
  second application instance.
- Import Qt WebEngine before application creation when the target is a
  `QWebEngineView`; the current probe intentionally avoids WebEngine. See
  [QGIS Plugin UI](qgis-plugin-ui.md).
- Keep visual iteration separate from behavior: signals, QGIS layer access,
  task execution, and bridge calls need normal fixture-driven tests. The agent
  may change visual parameters, not executable Python or QGIS state.

## Production path

1. Restore the Pixi environment and run the existing headless SDK lifecycle
   gates tracked by TASK-1.
2. Add a real widget factory for one declarative `qgis_sdk.ui.Dialog` or one
   plugin dialog. Reuse `qgis_sdk._qt` rather than importing a second Qt binding
   path.
3. Add image and behavior fixtures: stable geometry/content checks for CI, PNG
   artifacts for review, and explicit golden screenshots only when rendering
   stability is proven across the supported Qt/QGIS environment.
4. Connect a vision reviewer through the probe's JSON command seam or a future
   in-process agent adapter. Require complete, schema-validated design output,
   a bounded iteration count, and a human review checkpoint.
5. Promote only approved design specs/templates into scaffold output. Do not
   let a model rewrite plugin code or bypass QGIS/Qt lifecycle rules.

The HTML/CSS/JS approach in `Archont561/archont561` uses a headless Chromium
screenshot script with a started dev server, fixed viewport, request
interception, and PNG output. The Qt equivalent is simpler for a single widget:
there is no browser server or DOM; `QWidget.grab()` is the capture primitive and
`QImage` is the analysis input. The reusable design is the bounded
capture/analyze/review/history loop, not the browser-specific tooling.

## Related records

- [QGIS Plugin UI](qgis-plugin-ui.md) — existing dialog, WebEngine, and bridge guidance.
- [Testing](testing.md) — offscreen Qt, QGIS lifecycle, serialized test rules.
- [D05: Threading](decisions/D05-threading.md) — Qt/QGIS thread affinity.
- [TASK-1](../backlog/tasks/task-1%20-%20Make%20the%20full%20QGIS%20SDK%20test%20suite%20headless%20and%20CI-green.md) — restore stable headless SDK execution.
- [TASK-23](../backlog/tasks/task-23%20-%20Refactor-every-test-suite-onto-property-based-and-fixture-driven-testing.md) — fixture-driven testing migration.
- [TASK-28](../backlog/tasks/task-28%20-%20Validate-an-agent-design-loop-for-a-headless-PyQt-widget.md) — feasibility spike and proof output.
