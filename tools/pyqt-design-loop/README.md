# PyQt UI design loop probe

This probe tests whether an agent loop can operate on a QGIS-style UI boundary:

1. Build one real custom-painted `QWidget` from a JSON `DesignSpec`.
2. Run it with Qt's offscreen platform.
3. Capture the widget itself with `QWidget.grab()`.
4. Analyze the resulting `QImage` and write metrics beside the PNG.
5. Ask a reviewer for the next design specification.
6. Repeat for a bounded number of iterations.

It uses a deterministic heuristic reviewer by default so the loop can be tested
without model credentials. A vision-capable agent can replace that reviewer with
`--reviewer-command`; the command receives a JSON payload on stdin containing the
absolute screenshot path, current spec, and metrics, and must return one complete
`DesignSpec` JSON object on stdout.

## Run in the Pixi/QGIS environment

The repository's QGIS environment supplies PyQt through QGIS. The probe prefers
`qgis.PyQt`, then tries standalone PyQt5, PyQt6, and PySide6:

```bash
QT_QPA_PLATFORM=offscreen python tools/pyqt-design-loop/design_loop.py \
  --iterations 4 --output /tmp/qgis-rs-qt-design-loop
```

The output contains `iteration-00.png`, `iteration-00.json`, `history.json`, and
`final-spec.json`. It is intentionally outside Git; screenshots are evidence,
not source fixtures.

For a QGIS plugin widget, replace `make_widget` with a factory that creates the
actual `QDialog`, `QWidget`, or `QDockWidget`. Keep the same `grab`/analysis/review
seam and run QGIS/Qt tests serialized with `QT_QPA_PLATFORM=offscreen`. QGIS
objects and application state must stay on Qt's owning thread.

## Model reviewer contract

Example command:

```bash
python my_vision_reviewer.py < /tmp/reviewer-input.json
```

The probe invokes a configured command once per iteration. The command receives:

```json
{
  "iteration": 0,
  "screenshot": "/absolute/path/iteration-00.png",
  "spec": {},
  "analysis": {},
  "instruction": "Return one complete DesignSpec JSON object..."
}
```

The command must emit only a complete design-spec JSON object. The loop does not
silently accept malformed or partial model output.

## Current limitation

This is an implementation feasibility probe, not a claim that visual quality can
be judged by numeric metrics alone. A useful production loop needs a vision-capable
reviewer plus deterministic constraints for size, contrast, content, and behavior.
The reviewer should propose visual changes only; widget behavior remains covered
by normal tests.
