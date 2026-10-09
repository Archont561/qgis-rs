---
id: TASK-54
title: Ship the qgis-sdk ui preview command
status: To Do
assignee: []
created_date: '2026-10-09 00:10'
updated_date: '2026-10-09 00:10'
labels:
  - qgis-sdk
  - ui
  - dev-tooling
  - headless
milestone: m-3
dependencies: []
documentation:
  - >-
    backlog/docs/ui/doc-10 -
    qgis-sdk-UI-Preview-CLI-and-Dev-Loop.md
  - >-
    backlog/docs/ui/doc-9 -
    Agent-Driven-PyQt-QGIS-Visual-Design-Loop-Spec.md
  - .knowledge/qgis-ui-agent-design-loop.md
  - .knowledge/testing.md
  - .knowledge/decisions/D05-threading.md
  - .knowledge/decisions/D10-xtask-over-shell-scripts.md
priority: medium
type: enhancement
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement `qgis-sdk ui preview` per doc-10: render one real plugin dialog, declarative spec, or `.ui` file headlessly (`QT_QPA_PLATFORM=offscreen`, `QWidget.grab()`) to PNG + doc-9 analysis JSON, and — with `--serve` — forward it to a browser with live interaction (`POST /events`, `GET /widget.png` polling or `GET /stream` SSE), including sandbox forwarding (`--host 0.0.0.0`, relative URLs only). This is the human-facing precursor of the TASK-29 design loop; the CLI shape converges with doc-9's run contract.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `qgis-sdk ui preview` renders a scaffolded plugin dialog (`dialogs/*_dialog.py`), a `--factory dotted:Class`, a `--spec spec.json` declarative Dialog, or a `.ui` file via `make_dialog`, headlessly in the pixi QGIS environment, writing `preview.png` + `preview.json` (doc-9 metrics) to `--output`.
- [ ] #2 `--serve` serves the control page, `GET /widget.png`, `GET /spec`, `POST /spec` (fail-closed validation), and the interaction channel `POST /events` + `GET /stream` (SSE).
- [ ] #3 Interactions drive the real widget: browser-coordinate events are mapped to widget pixels, hit-tested with `widgetAt`/`childAt`, and dispatched with `QTest.mouseClick`/`QTest.keyClicks` on the GUI thread; a click changes widget state and the next frame shows it.
- [ ] #4 Sandbox forwarding works: `--host 0.0.0.0` binds all interfaces, the page uses relative URLs only, and the preview is reachable through a plain-HTTP proxy (verified against the Arena live-preview proxy).
- [ ] #5 Failure is explicit: missing Qt/QGIS, an unloadable target, or a failed capture exits non-zero with a clear error; nothing prints a warning and reports success.
- [ ] #6 Tests: pure-layer tests for spec loading/validation, analysis metrics, CLI wiring, and endpoint routing; qt-layer tests for offscreen capture and the click round-trip; WebEngine targets stay behind the opt-in gate.
- [ ] #7 Package scripts `ui:preview` and `ui:serve` exist in `py-packages/qgis-sdk/package.json` (wrapped in `pixi run -e default`, per D10), runnable via `bun --filter=qgis-sdk-py run ui:preview`.
- [ ] #8 The command is documented in `docs/src/content/docs/cli/plugin.mdx` and the plugin-development guide, without making model credentials a test prerequisite.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Add `qgis_sdk/ui/preview.py` (lazy Qt imports; pure helpers importable without Qt), wire the `ui preview` subcommand in `cli.py` (thin handler, like `ui add-dialog`), add the two package.json scripts, then tests by layer. Keep all Qt access behind `qgis_sdk._qt`; reuse one `QApplication`; start `QgsApplication` only for targets that need QGIS objects.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
doc-10 is the contract, including the "why a Qt dialog cannot be ported to the browser directly" section and the sandbox forwarding rules. Sandbox probe evidence (offscreen grab, QTest dispatch, hit-testing, `0.0.0.0` + relative-URL proxy reachability) is recorded in doc-10's feasibility section; the probe itself lives outside the repository.
<!-- SECTION:NOTES:END -->
