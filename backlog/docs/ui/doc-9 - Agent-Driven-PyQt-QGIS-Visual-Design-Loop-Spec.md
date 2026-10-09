---
id: doc-9
title: Agent-Driven PyQt/QGIS Visual Design Loop Specification
type: specification
created_date: '2026-10-08 22:30'
---

# Agent-driven PyQt/QGIS visual design loop specification

## Status

This document is a **specification, not shipped tooling**. The repository does
not carry a design-loop tool under `tools/` at this time. The loop was
validated as a feasibility probe (TASK-28, Done); the probe code was removed
from the repository on 2026-10-08 and its validated design was moved here.
TASK-29 builds the loop against a real QGIS widget once the declarative UI
contract (TASK-36, doc-6) is ready. The durable rationale and run evidence
remain in
[.knowledge/qgis-ui-agent-design-loop.md](../../../.knowledge/qgis-ui-agent-design-loop.md).

## Purpose

The design loop is a bounded agent workflow that improves the visual design of
one QGIS-style UI element without a desktop screenshot utility or a browser:

1. Build one real widget from a JSON `DesignSpec`.
2. Run it headlessly with Qt's offscreen platform.
3. Capture the widget itself with `QWidget.grab()`.
4. Analyze the resulting `QImage` and write metrics beside the PNG.
5. Ask a reviewer for the next design specification.
6. Repeat for a bounded number of iterations.

The reviewer is deterministic by default so the loop is testable without model
credentials. A vision-capable agent can replace that reviewer through a command
seam. The loop changes visual parameters only; widget behavior remains covered
by ordinary fixture-driven tests.

## Loop contract

```text
DesignSpec
    │
    ▼
widget factory ──► QApplication / QgsApplication owner thread
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

## DesignSpec model

A `DesignSpec` is one complete JSON object of visual parameters. The probe
model used these fields, and the production model generalizes them onto the
typed widget specs from TASK-36/doc-6:

```text
width, height          canvas size in pixels
background, surface    page and card colours, six-digit hex
accent, text, muted    action, body-text, and secondary-text colours, hex
margin, radius         content spacing and corner radius in pixels
title_size, title      heading size in points and heading text
subtitle, button       secondary text and primary action label
```

Validation rules:

- Unknown fields fail closed: a spec carrying fields outside the model is
  rejected, never partially applied.
- Colours are six-digit hexadecimal; anything else is rejected.
- A reviewer returns **one complete** spec object. Malformed or partial model
  output stops the loop; it is never silently accepted.

## Loop seams

1. **Widget factory:** constructs the actual `QDialog`, `QWidget`,
   `QDockWidget`, or plugin panel from a validated design model. The probe used
   one custom-painted widget; production code reuses `qgis_sdk._qt` and the
   existing application lifecycle instead of importing a second Qt binding
   path.
2. **Capture:** calls `show()`, processes pending Qt events, and uses `grab()`
   on the widget. This captures the widget in its real Qt style without X11,
   Wayland, Chromium, or a full-screen desktop capture.
3. **Analysis:** calculates deterministic facts from the `QImage`: dimensions,
   background colour, mean luminance, luminance standard deviation,
   non-background ratio, and WCAG contrast ratios for text, muted text, accent,
   and white-on-accent, plus a heuristic score and an issue list. Probe
   thresholds: text contrast 4.5 (WCAG AA body text), muted contrast 3.0,
   white-on-accent 4.5, margin at least 24 px, title size at least 24 pt, canvas
   at least 640 x 360 px. These checks are guardrails, not a substitute for
   visual judgment.
4. **Review:** a deterministic heuristic reviewer supports smoke tests. An
   external reviewer receives the screenshot path, current spec, metrics, and a
   visual-only instruction, then returns one complete spec. Model output is
   validated before any Qt object is constructed from it.
5. **History:** preserves every screenshot, spec, and analysis for comparison:
   `iteration-NN.png`, `iteration-NN.json`, `history.json`, `final-spec.json`,
   and `binding.txt`. Output is written outside Git; screenshots are evidence
   and review artifacts, not source fixtures or automatically accepted golden
   tests.
6. **Approval:** human review is required before a spec or template change is
   promoted into scaffold output.

## Reviewer command contract

The loop invokes a configured reviewer command once per iteration. The command
receives a JSON payload on stdin:

```json
{
  "iteration": 0,
  "screenshot": "/absolute/path/iteration-00.png",
  "spec": {},
  "analysis": {},
  "instruction": "Return one complete DesignSpec JSON object. Preserve behavior and improve visual design only."
}
```

The command must emit only a complete design-spec JSON object on stdout. A
non-zero exit, non-JSON output, or a schema violation fails the loop closed.

## Run contract

- Set `QT_QPA_PLATFORM=offscreen` for headless runs; the loop sets it by
  default.
- Resolve the Qt binding in order: `qgis.PyQt` (inside QGIS), then standalone
  PyQt5, PyQt6, and PySide6. Record the binding used in `binding.txt`. A missing
  binding is an explicit error listing what was tried; there is no hidden
  fallback.
- Reuse one `QApplication` instance (`QApplication.instance() or
  QApplication([])`); never create a second application object.
- CLI shape: `design_loop.py --iterations N --output DIR [--reviewer-command CMD]`
  with a default of 4 iterations and a minimum of 1.
- Stop at the iteration bound, or earlier when the spec stabilizes.
- Run inside the repository's Pixi/QGIS environment. QGIS objects and
  application state stay on Qt's owning thread, and QGIS widget tests run
  serialized because application state is process-wide (see
  [Testing](../../../.knowledge/testing.md) and
  [D05](../../../.knowledge/decisions/D05-threading.md)).

## Shipped command and browser interaction

The loop converges on a shipped command, specified in
[doc-10](doc-10%20-%20qgis-sdk-UI-Preview-CLI-and-Dev-Loop.md) and tracked by
TASK-54: `qgis-sdk ui preview` renders one widget headlessly to PNG + analysis
JSON, and `--serve` forwards it to a browser. The run contract above is the
shared contract — the command's CLI shape (`--iterations`, `--output`,
`--reviewer-command`) extends it without changing it.

The preview adds the human-in-the-loop counterpart of the reviewer seam: the
browser posts interaction events (`POST /events`, widget-pixel coordinates),
the server dispatches them with `QTest.mouseClick`/`QTest.keyClicks` on the GUI
thread, and frames reach the browser by polling (`GET /widget.png`) or SSE
(`GET /stream`). For sandboxes the server binds `0.0.0.0` and the page uses
relative URLs only, so the preview works through a proxy; WebSocket support
through preview proxies is unverified and the contract does not rely on it.
Interactive preview is evidence for a human reviewer; widget behavior remains
covered by ordinary fixture-driven tests.

## Constraints and safety rules

- Bounded iteration count; no unbounded self-improvement.
- Complete, schema-validated output only; fail closed on malformed reviewer
  output.
- No model-generated code execution. The reviewer may change visual parameters
  such as spacing, palette, font sizes, layout mode, and component arrangement.
  It must not change Python code, QGIS behavior, signal wiring, task execution,
  bridge methods, or filesystem/process policy.
- Visual iteration stays separate from behavior: signals, QGIS layer access,
  task execution, and bridge calls need normal fixture-driven tests.
- Screenshots are review artifacts; explicit golden screenshots are added only
  when rendering stability is proven across the supported Qt/QGIS environment.
- Visual metrics supplement human review and do not claim complete visual
  understanding.

## Feasibility evidence (TASK-28)

The probe validated the loop mechanics headlessly with real PyQt5 (a temporary
installation and an offscreen OpenGL stub outside the repository; the base shell
lacks Qt and `libGL.so.1`):

- 4 unit tests passed: contrast against the WCAG reference, spec JSON
  round-trip, heuristic improvement of the initial spec, and fail-closed
  rejection of unknown fields.
- Real offscreen run: iteration 0 produced a 520 x 300 PNG with score `0.5330`
  (low contrast, cramped spacing, weak hierarchy); iteration 1 produced a
  720 x 420 PNG with score `1.0000` and no remaining heuristic issues.
- The external reviewer seam was smoke-tested with a temporary command that
  received the stdin JSON payload and returned a complete spec.
- Limitation: this validates the loop mechanics and the rendering seam, not
  QGIS integration. The normal validation path remains the repository's Pixi
  QGIS environment.

## Acceptance criteria for the implementation

The implementation is owned by
[TASK-29](../../tasks/task-29%20-%20Connect-a-vision-reviewer-to-a-real-QGIS-widget-design-loop.md),
which requires: a real `qgis.PyQt` widget factory reusing the existing
`QApplication`/`QgsApplication` lifecycle, serialized with
`QT_QPA_PLATFORM=offscreen`; PNG and JSON evidence per bounded iteration and a
reviewable final diff; a reviewer adapter that returns schema-validated visual
parameters only and fails closed on malformed or behavioral edits; widget
behavior covered by ordinary fixture-driven tests; and a run inside the Pixi
QGIS environment without making model credentials a test prerequisite.

## Related records

- [doc-6 — QGIS SDK Native UI Kit and Visual Design Loop Strategy](doc-6%20-%20QGIS-SDK-Native-UI-Kit-and-Visual-Design-Loop-Strategy.md) — product strategy and loop constraints.
- [TASK-28 — Validate an agent design loop for a headless PyQt widget](../../tasks/task-28%20-%20Validate-an-agent-design-loop-for-a-headless-PyQt-widget.md) — feasibility spike (Done); probe removed, design moved here.
- [TASK-29 — Connect a vision reviewer to a real QGIS widget design loop](../../tasks/task-29%20-%20Connect-a-vision-reviewer-to-a-real-QGIS-widget-design-loop.md) — real QGIS integration and optional vision review (To Do).
- [.knowledge/qgis-ui-agent-design-loop.md](../../../.knowledge/qgis-ui-agent-design-loop.md) — durable rationale, loop contract, and run evidence.
- [D05 — Threading](../../../.knowledge/decisions/D05-threading.md) — Qt/QGIS thread affinity.
- [Testing](../../../.knowledge/testing.md) — offscreen Qt, QGIS lifecycle, serialized test rules.
- [doc-10 — qgis-sdk UI Preview CLI and Dev Loop](doc-10%20-%20qgis-sdk-UI-Preview-CLI-and-Dev-Loop.md) — the shipped `ui preview` command and its browser interaction channel.
- [TASK-54 — Ship the qgis-sdk ui preview command](../../tasks/task-54%20-%20Ship-the-qgis-sdk-ui-preview-command.md) — the human-facing precursor of TASK-29.
