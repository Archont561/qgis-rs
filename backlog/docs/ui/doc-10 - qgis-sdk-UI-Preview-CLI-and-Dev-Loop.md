---
id: doc-10
title: qgis-sdk UI Preview CLI and Dev Loop
type: specification
created_date: '2026-10-09 00:10'
---

# qgis-sdk UI preview CLI and dev loop

## Status

Specification for the `qgis-sdk ui preview` command (TASK-54). It is the
human-facing counterpart of the agent design loop specified in
[doc-9](doc-9%20-%20Agent-Driven-PyQt-QGIS-Visual-Design-Loop-Spec.md): the loop
iterates on a design spec automatically; the preview renders one real widget
for a human, in a browser, with live interaction.

## Why a Qt dialog cannot be ported to the browser directly

A PyQt dialog is not web content. There is no DOM, no stylesheet engine, and no
way for a browser to instantiate or drive a `QObject`; Qt has no remote
framebuffer protocol of its own. So the preview does not port the dialog — it
keeps the dialog as the single source of truth and forwards its *pixels* and
*events*:

```text
browser ──POST /events {x, y, type}──▶  input queue ──▶ QTimer (GUI thread)
                                                            │ QTest.mouseClick /
                                                            │ keyClicks, hit-test
                                                            │ via widgetAt/childAt
browser ◀──GET /stream (SSE) or /widget.png (poll)──  latest frame (PNG)
```

The browser is a thin display plus an input forwarder. Everything else — widget
state, signals, validation, `QSettings` — lives in Qt, in the process that owns
the widget.

## Command API

```text
qgis-sdk ui preview [path] [--spec spec.json] [--factory dotted:Class]
                    [-o|--output DIR] [--serve] [--host HOST] [--port PORT]
```

- `path` (default `.`): plugin directory; auto-discovers `dialogs/*_dialog.py`
  (the `uic.loadUiType` + `WA_DeleteOnClose` + `QSettings` scaffold pattern) or
  a `.ui` file loadable through `make_dialog`.
- `--factory my_plugin.dialogs.main_dialog:MainDialog`: explicit dialog class.
- `--spec spec.json`: build a declarative `qgis_sdk.ui.Dialog` from a design
  spec instead of loading a plugin dialog.
- Target resolution order: `--factory` → `--spec` → auto-discovery.
- `-o/--output DIR` (default `preview`): writes `preview.png` + `preview.json`
  (spec + doc-9 analysis metrics) and exits.
- `--serve`: start the browser-forwarding dev server instead of writing files.
- `--host` (default `127.0.0.1`): bind address. Use `--host 0.0.0.0` when the
  browser is not on the same machine — sandboxes, containers, remote previews.
- `--port` (default `8000`).

Future loop mode (TASK-29): `--iterations N --reviewer-command CMD` converge
with doc-9's run contract, so the probe and the shipped command stay one
contract.

### Serve endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | Control page (auto-refresh, spec controls, relative URLs only) |
| `GET /widget.png` | Live render: `show()` → `processEvents()` → `grab()` → PNG |
| `GET /stream` | Same frame as an SSE stream (`text/event-stream`) for push |
| `GET /spec` | Current spec + render count |
| `POST /spec` | Validated design-spec update (fail closed: unknown fields, bad colours, out-of-range ints → 400) |
| `POST /events` | Interaction events in widget-pixel coordinates |

## Render contract

- `QT_QPA_PLATFORM=offscreen` by default; one `QApplication` reused
  (`QApplication.instance() or QApplication([])`).
- `QgsApplication` only when the target widget needs QGIS objects; a plugin
  adapter reuses the existing application/QGIS lifecycle and never creates a
  second application instance.
- All Qt imports go through `qgis_sdk._qt` (the single binding funnel:
  `qgis.PyQt` → PyQt6 → PySide6 → PyQt5). No second binding-detection path.
- The analysis JSON beside the PNG carries the doc-9 metrics: dimensions,
  sampled contrast ratios, heuristic score, issue list.
- Fail closed: missing Qt/QGIS, an unloadable target, or a failed capture is an
  explicit error with a non-zero exit — never a printed warning and a fake
  success (doc-6 failure behavior).

## Interaction contract

- The page converts browser coordinates to widget pixels using the widget's
  natural size (served by `GET /spec`), because CSS scales the `<img>`.
- The server hit-tests with `widgetAt`/`childAt` and dispatches with
  `QTest.mouseClick`/`QTest.keyClicks` — never hand-rolled single
  `QMouseEvent`s, which do not trigger button logic without the
  press→release grab sequence (verified in the sandbox probe).
- Event vocabulary: click, double-click, hover, wheel, key clicks (Tab order,
  Enter, Esc), text input. A semantic complement (`{field: objectName,
  value}` → `setText`/`setValue`) is optional for robustness; pixel events are
  the primary surface because hit targets are what a design review judges.
- Threading: `ThreadingHTTPServer` + a thread-safe input queue + a `QTimer` on
  the GUI thread (~50 ms) that drains the queue and re-renders into a
  latest-frame buffer. All Qt objects are touched only on the GUI thread
  (D05/D12; doc-9 constraints). A single-threaded server cannot hold an SSE
  stream and serve requests at once — hence the queue.
- Latency: polling mode is up to one refresh interval (~1.5 s) click-to-frame;
  SSE push is ~50–100 ms. SSE is plain HTTP and proxy-safe; WebSocket support
  through preview proxies is unverified, so the contract does not build on it.

## Browser forwarding for sandboxes

- Bind `0.0.0.0` when the browser is remote (`--host 0.0.0.0`); the sandbox
  preview proxy exposes the port as a live preview URL.
- The page uses **relative URLs only**; browser-facing code never calls
  `localhost`/`127.0.0.1` to reach the server. Same-origin requests work
  through any proxy that forwards plain HTTP.
- No host/origin allowlist: the server accepts any `Host` header.
- `Cache-Control: no-store` on frames; clients cache-bust with a query
  parameter.

## Dev loop

```text
qgis-sdk new my_plugin          # scaffold (dialogs/main_dialog.py + ui/main_dialog.ui)
… edit ui/main_dialog.ui …       # Qt Designer XML, no pyuic5 step
qgis-sdk ui preview .           # one-shot: preview/preview.png + preview.json
qgis-sdk ui preview --serve     # live page: auto-refresh + spec controls + interactions
```

Package scripts (the package's own `package.json`, wrapped in
`pixi run -e default`; per D10, package verbs stay out of root pixi.toml and
xtask):

```json
"ui:preview": "pixi run -e default env QT_QPA_PLATFORM=offscreen qgis-sdk ui preview",
"ui:serve": "pixi run -e default env QT_QPA_PLATFORM=offscreen qgis-sdk ui preview --serve --host 0.0.0.0"
```

Run with `bun --filter=qgis-sdk-py run ui:preview` (turbo only fans out `test`;
other scripts are opt-in `bun run`).

## Testing

- Pure layer (no Qt import): spec loading/validation, analysis metrics, CLI
  parser wiring, endpoint routing.
- Qt layer (`QT_QPA_PLATFORM=offscreen`): capture produces a valid PNG; a
  `QTest.mouseClick` round-trip changes widget state and the next frame shows
  it.
- WebEngine targets stay behind the opt-in `test:webengine` gate.
- CLI tests call the real entry point and assert exit codes and output.

## Feasibility evidence (sandbox probe, outside the repository)

A scratch server outside the repository verified, with standalone PyQt5
5.15.14 and an offscreen `libGL` stub: `QWidget.grab()` produces valid PNGs
under `QT_QPA_PLATFORM=offscreen`; `QTest.mouseClick` fires `clicked` and
`QTest.keyClicks` types into a `QLineEdit` offscreen; `childAt` hit-tests
correctly; a hand-rolled single `QMouseEvent` does not trigger button logic;
plain-HTTP request/response and a `0.0.0.0` bind are reachable through the
sandbox preview proxy. The repository's own run path is the Pixi QGIS
environment (`qgis.PyQt`, real `libGL` via libglvnd — no stub).

## Related records

- [doc-9 — Agent-Driven PyQt/QGIS Visual Design Loop Specification](doc-9%20-%20Agent-Driven-PyQt-QGIS-Visual-Design-Loop-Spec.md) — the automated loop this command complements.
- [doc-6 — QGIS SDK Native UI Kit and Visual Design Loop Strategy](doc-6%20-%20QGIS-SDK-Native-UI-Kit-and-Visual-Design-Loop-Strategy.md)
- [TASK-54 — Ship the qgis-sdk ui preview command](../../tasks/task-54%20-%20Ship-the-qgis-sdk-ui-preview-command.md)
- [TASK-29 — Connect a vision reviewer to a real QGIS widget design loop](../../tasks/task-29%20-%20Connect-a-vision-reviewer-to-a-real-QGIS-widget-design-loop.md)
- [TASK-36 — Define the native-first declarative QGIS SDK UI contract](../../tasks/task-36%20-%20Define-the-native-first-declarative-QGIS-SDK-UI-contract.md)
- [.knowledge/qgis-ui-agent-design-loop.md](../../../.knowledge/qgis-ui-agent-design-loop.md)
- [D05 — Threading](../../../.knowledge/decisions/D05-threading.md), [D10 — xtask over Shell Scripts](../../../.knowledge/decisions/D10-xtask-over-shell-scripts.md)
- [Testing](../../../.knowledge/testing.md)
