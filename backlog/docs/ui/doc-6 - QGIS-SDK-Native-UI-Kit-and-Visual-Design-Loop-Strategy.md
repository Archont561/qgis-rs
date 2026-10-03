---
id: doc-6
title: QGIS SDK Native UI Kit and Visual Design Loop Strategy
type: specification
created_date: '2026-10-03 10:00'
---

# QGIS SDK native UI kit and visual design loop strategy

## Product recommendation

`qgis-sdk` should ship a **native-first, declarative, QGIS-aware plugin UI kit**. It should not become a replacement for Qt Widgets, a duplicate of the QGIS GUI API, or a second Processing parameter framework.

The SDK should make common plugin UIs concise and testable while preserving escape hatches to native Qt and QGIS widgets:

```text
qgis_sdk.ui
├── core       Dialog, Panel, Dock, Form, Section, Tabs
├── fields     text, number, choice, file, layer, field, CRS, extent, expression
├── qgis       native QGIS widget adapters and map-canvas helpers
├── actions    menus, toolbars, shortcuts, icons
├── feedback   progress, cancellation, messages, errors
├── state      validation, model binding, QSettings persistence
├── theme      QGIS palette, spacing, density, accessibility
└── web        optional QWebEngine/QWebChannel support
```

The current `Dialog`, `FieldSpec`, `field`, `layout`, `Button`, `WebDialog`, bridge, and `qgis_sdk.qt` APIs are useful starting points. They should be stabilized behind a compatibility facade while their implementation is split into focused modules.

## Design principles

- Native Qt/QGIS first; WebEngine is optional.
- Declarative specifications are separate from Qt widget construction.
- Field values are typed and validated; callers do not need to inspect widget internals.
- QGIS-native controls are adapted, not reimplemented.
- Processing algorithms continue to use QGIS's parameter system.
- Visual design changes do not change plugin behavior.
- Pure UI specifications can be tested without Qt or QGIS.
- Real Qt/QGIS lifecycle tests remain explicit and serialized.
- Public imports stay compatible during decomposition.
- Model-generated visual changes are constrained to validated design data, never executable plugin code.

## Built-in UI surface

### Core containers

The first-class containers should cover common QGIS plugin patterns:

```text
Dialog        modal or modeless QDialog wrapper
Panel         reusable QWidget content
Dock          QDockWidget integration
Form          typed field collection and validation
Section       labelled/collapsible form group
Tabs          tabbed form or settings page
ActionBar     apply/cancel/ok/custom actions
EmptyState    no-data state
LoadingState  task-in-progress state
ErrorState    recoverable error state
```

Target usage:

```python
Dialog(
    title="Buffer features",
    content=Form(
        field.layer("input", label="Input layer", layer_type="vector"),
        field.number("distance", label="Distance", default=10, minimum=0),
        field.crs("output_crs", label="Output CRS"),
    ),
    actions=[action.cancel(), action.apply(), action.ok()],
)
```

The exact API may retain the current `layout=` shape for compatibility, but the internal model should distinguish content, fields, validation, and actions.

### Field catalog

Basic fields:

```text
text
multiline
integer
number
boolean
choice
file
folder
color
date
datetime
password
```

QGIS-aware fields:

```text
layer
field
CRS
extent
expression
geometry type
feature source
map scale
raster band
```

Fields should produce typed values:

```text
layer       -> QgsMapLayer or scoped layer handle
number      -> int/float
CRS         -> QgsCoordinateReferenceSystem
extent      -> QgsRectangle
expression  -> validated expression model
```

Use native QGIS controls when available, including layer, field, CRS, extent, and map-canvas widgets. The SDK owns the adapter and validation contract, not the underlying QGIS widget implementation.

### Processing integration

Do not create a duplicate Processing UI system.

```text
QgsProcessingAlgorithm parameters
    -> QGIS generates standard Processing UI

Custom plugin workflow
    -> qgis_sdk.ui.Form
```

Add an adapter only where it reduces duplication:

```python
form = Form.from_processing_algorithm(MyAlgorithm())
parameters = form.values()
MyAlgorithm().check_parameter_values(parameters)
```

QGIS remains authoritative for Processing parameter definitions, algorithm dialogs, batch behavior, and model-builder integration.

## Validation and state

The UI kit needs a separate form model:

```text
FieldSpec
    -> FieldState
    -> native Qt widget
    -> typed value
```

Support:

- required values;
- field-level and form-level validation;
- min/max and type constraints;
- dirty state;
- reset and apply-without-closing;
- async validation;
- QSettings persistence;
- explicit model binding;
- accessible error messages.

Example:

```python
field.text(
    "name",
    required=True,
    validator=validators.plugin_name,
)

field.number(
    "distance",
    minimum=0,
    maximum=100000,
)
```

Return structured validation results rather than only raising arbitrary UI exceptions:

```text
ValidationResult(
    valid=False,
    field="distance",
    message="Distance must be greater than zero",
)
```

## Plugin host integration

Ship a small host integration layer for actions, docks, menus, and lifecycle:

```text
plugin init
  -> register actions/docks
  -> create UI lazily
  -> run tasks
  -> disconnect signals
  -> remove actions/docks
  -> unload
```

The host layer should provide:

- menu actions;
- toolbar actions;
- icons;
- keyboard shortcuts;
- docks;
- plugin-owned settings;
- enable/disable conditions;
- status-bar messages;
- notifications;
- task progress;
- deterministic cleanup.

Do not require every plugin to know QGIS registry and signal cleanup details.

## Feedback and long-running operations

Long-running work must remain off the GUI thread. The UI API should integrate with the existing task system:

```python
with dialog.task("Processing layers") as task:
    for index, layer in enumerate(layers):
        if task.is_canceled():
            break
        process(layer)
        task.progress(index / len(layers) * 100)
```

The feedback surface should expose progress, cancellation, logs, warnings, errors, completion, and retry without requiring a plugin to manually wire every signal.

## Theme and accessibility

Ship a small theme policy, not a custom visual framework:

```text
QGIS host palette
    -> SDK spacing/density policy
    -> native Qt widgets
```

Support:

- QGIS light/dark palette;
- high-DPI scaling;
- compact and default density;
- standard spacing;
- visible keyboard focus;
- keyboard navigation;
- accessible labels and descriptions;
- native platform dialogs;
- standard QGIS icons.

Avoid hard-coded colours and large CSS-like styling systems for native Qt widgets. Theme tokens should be data that can be checked by tests and reviewed by the visual loop.

## Optional Web UI

Keep WebEngine and bridge support in an optional layer:

```text
qgis_sdk.ui              native Qt/QGIS UI
qgis_sdk.ui.web          optional WebEngine UI
qgis_sdk.bridge          typed Python <-> JavaScript bridge
```

Use WebEngine for complex charts, web maps, modern frontend frameworks, and rich HTML layouts. Use native Qt for settings, Processing-style forms, layer/CRS selection, simple dialogs, progress, and QGIS-integrated workflows.

Ordinary UI tests must not require Qt WebEngine. WebEngine has a separate startup, rendering, and headless test gate.

## Visual design loop

The agent design loop is a bounded visual iteration workflow:

```text
DesignSpec
    |
    v
widget factory
    |
    v
QApplication/QgsApplication owner thread
    |
    v
QWidget.grab() -> PNG + QImage
    |
    +-- deterministic metrics and constraints
    |
    v
heuristic or vision reviewer
    |
    v
validated next DesignSpec
```

The existing feasibility probe is in `tools/pyqt-design-loop/` and is tracked by TASK-28. It proves that one custom-painted PyQt widget can:

- run with `QT_QPA_PLATFORM=offscreen`;
- capture itself with `QWidget.grab()`;
- write PNG and JSON history;
- calculate deterministic metrics;
- improve a deliberately weak design;
- accept an external reviewer command that returns a complete JSON spec.

The real QGIS integration is tracked by TASK-29.

### Loop seams

1. **Widget factory:** creates a real `QDialog`, `QWidget`, `QDockWidget`, or plugin panel from a validated design model.
2. **Capture:** shows the widget, processes Qt events, and captures the widget with `grab()`.
3. **Analysis:** checks dimensions, spacing, sampled luminance/contrast, required content, and stable geometry.
4. **Review:** deterministic reviewer for tests; optional vision-capable reviewer for design work.
5. **History:** retains each screenshot, spec, and analysis for comparison.
6. **Approval:** human review is required before promoting a spec or template change.

The reviewer may change visual parameters such as spacing, palette, font sizes, layout mode, and component arrangement. It must not change Python code, QGIS behavior, signal wiring, task execution, bridge methods, or filesystem/process policy.

### Loop constraints

- bounded iteration count;
- complete schema-validated output;
- no arbitrary model-generated code execution;
- no hidden QGIS/Qt fallback;
- stable content and behavior tests remain separate;
- screenshots are review artifacts, not automatically accepted golden tests;
- visual metrics supplement human review and do not claim complete visual understanding.

## Recommended implementation modules

Refactor the current UI implementation behind compatibility exports:

```text
qgis_sdk/ui/
├── __init__.py
├── specs.py          # FieldSpec, FormSpec, ActionSpec
├── fields.py         # field builders and validators
├── forms.py          # Form and model binding
├── dialogs.py        # Dialog lifecycle
├── panels.py         # Panel and Dock
├── qgis_widgets.py   # native QGIS widget adapters
├── actions.py        # menus, actions, toolbars
├── feedback.py       # progress and task integration
├── state.py          # QSettings and state persistence
├── theme.py          # palette, spacing, accessibility
├── qt_backend.py     # _qt funnel and native construction
└── web.py            # optional WebEngine/QWebChannel
```

`qgis_sdk.ui` remains the stable public facade. Internal modules may evolve independently.

## Failure behavior

A missing Qt/QGIS runtime must be explicit. A real dialog construction failure must not be hidden by printing an error and returning `Accepted`. Use one of:

```text
pure unit test -> injected fake dialog
Qt runtime     -> real dialog
missing Qt     -> clear PyQgisImportError or explicit marked skip
```

This prevents a broken UI from appearing to succeed in tests.

## Testing requirements

- Pure UI specs and validators run without Qt.
- Fake dialogs and fields test plugin behavior through public values/actions.
- Qt widget tests use `QApplication` and `QT_QPA_PLATFORM=offscreen`.
- QGIS widget tests use a serialized `QgsApplication` fixture.
- WebEngine tests use a separate optional gate.
- The visual loop tests screenshot capture and deterministic constraints.
- Bridge behavior uses the shared Python/TypeScript bridge contract from [doc-5](../testing/doc-5%20-%20QGIS-SDK-Testing-Utilities-and-Cross-Language-Bridge-Contracts.md).
- Existing generated plugin examples remain golden/fixture-tested.

## Implementation sequence

1. Stabilize the current public UI imports and write characterization tests.
2. Extract specs, fields, forms, dialogs, and Qt construction without changing behavior.
3. Add typed values, validation, state binding, and persistence.
4. Add QGIS-native layer, field, CRS, extent, and expression adapters.
5. Add plugin shell actions, docks, feedback, theme, and cleanup.
6. Integrate Processing parameter definitions without duplicating QGIS's UI system.
7. Integrate the real QGIS widget factory with the visual design loop.
8. Keep WebEngine/bridge functionality optional and migrate it to the shared bridge contract.
9. Remove unsafe fallback behavior only after compatibility and integration gates are green.
