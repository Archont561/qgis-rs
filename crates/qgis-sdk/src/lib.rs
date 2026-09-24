//! qgis-sdk Rust core — native-speed helpers for the Python plugin SDK.
//!
//! This crate provides:
//! - PyO3 bindings for plugin metadata, validation, and scaffolding at native speed
//! - Shared logic for the `qgis-plugin` / `qgis-sdk` CLI binaries
//! - UI scaffolding (dialogs via .ui, WebEngine HTML + QWebChannel)
//!
//! The Python package `qgis_sdk` imports this as `qgis_sdk._core` when built
//! with maturin, otherwise falls back to pure Python.

// pyo3's `#[pyfunction]`/`#[pymethods]` wrappers perform an identity
// `From<PyErr> for PyErr` conversion for the `PyResult<T>` alias; clippy's
// `useless_conversion` flags it but `#[allow]` on the item does not reach the
// macro output (PyO3/pyo3#4828, fixed upstream in 0.23.5). Module-level allow
// is the documented workaround.
#![allow(clippy::useless_conversion)]

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::path::{Path, PathBuf};

// ── Metadata handling (native speed) ────────────────────────────────────────

#[pyclass(name = "MetadataField")]
#[derive(Clone, Debug)]
pub struct PyMetadataField {
    #[pyo3(get)]
    pub attr: String,
    #[pyo3(get)]
    pub key: String,
}

#[pymethods]
impl PyMetadataField {
    #[new]
    fn new(attr: String, key: String) -> Self {
        Self { attr, key }
    }
    fn __repr__(&self) -> String {
        format!("MetadataField(attr={}, key={})", self.attr, self.key)
    }
}

const METADATA_FIELDS: &[(&str, &str)] = &[
    ("name", "name"),
    ("qgis_min_version", "qgisMinimumVersion"),
    ("qgis_max_version", "qgisMaximumVersion"),
    ("description", "description"),
    ("about", "about"),
    ("version", "version"),
    ("author", "author"),
    ("email", "email"),
    ("category", "category"),
    ("tags", "tags"),
    ("homepage", "homepage"),
    ("repository", "repository"),
    ("tracker", "tracker"),
    ("experimental", "experimental"),
    ("deprecated", "deprecated"),
    ("has_processing_provider", "hasProcessingProvider"),
    ("server", "server"),
];

#[pyfunction]
fn metadata_fields() -> Vec<PyMetadataField> {
    METADATA_FIELDS
        .iter()
        .map(|(attr, key)| PyMetadataField {
            attr: attr.to_string(),
            key: key.to_string(),
        })
        .collect()
}

#[pyfunction]
fn render_metadata_from_dict(py_dict: &Bound<'_, pyo3::types::PyDict>) -> PyResult<String> {
    let mut lines = vec!["[general]".to_string()];
    for (attr, key) in METADATA_FIELDS {
        if let Some(value) = py_dict.get_item(attr)? {
            if value.is_none() {
                continue;
            }
            let normalized = if let Ok(b) = value.extract::<bool>() {
                if b {
                    "True".to_string()
                } else {
                    "False".to_string()
                }
            } else if let Ok(s) = value.extract::<String>() {
                let trimmed = s.trim().to_string();
                if trimmed.is_empty() {
                    continue;
                }
                trimmed
            } else {
                if let Ok(list) = value.extract::<Vec<String>>() {
                    let joined = list
                        .into_iter()
                        .filter(|s| !s.trim().is_empty())
                        .collect::<Vec<_>>()
                        .join(", ");
                    if joined.is_empty() {
                        continue;
                    }
                    joined
                } else {
                    value.to_string()
                }
            };
            lines.push(format!("{key}={normalized}"));
        }
    }
    Ok(lines.join("\n") + "\n")
}

#[pyfunction]
fn validate_plugin_structure(path: &str) -> PyResult<Vec<String>> {
    let mut errors = Vec::new();
    let base = Path::new(path);

    if !base.exists() {
        return Err(PyValueError::new_err(format!(
            "path does not exist: {path}"
        )));
    }

    // Check metadata.txt if exists
    let metadata_path = if base.join("metadata.txt").exists() {
        base.join("metadata.txt")
    } else {
        base.join("src").join("metadata.txt")
    };

    if metadata_path.exists() {
        match std::fs::read_to_string(&metadata_path) {
            Ok(content) => {
                if !content.contains("[general]") {
                    errors.push("metadata.txt missing [general] section".to_string());
                }
                if !content.contains("name=") {
                    errors.push("metadata.txt missing name".to_string());
                }
                if !content.contains("version=") {
                    errors.push("metadata.txt missing version".to_string());
                }
            }
            Err(e) => errors.push(format!("cannot read metadata.txt: {e}")),
        }
    }

    // UI checks — warn if ui/ exists but no .ui files, or web/ exists but no html
    if base.join("ui").exists()
        || base
            .join(base.file_name().unwrap_or_default())
            .join("ui")
            .exists()
    {
        // Try both plugin root and nested package dir
        let ui_dirs = vec![
            base.join("ui"),
            base.join(base.file_name().unwrap_or_default()).join("ui"),
        ];
        for ui_dir in ui_dirs {
            if ui_dir.exists() {
                let has_ui = std::fs::read_dir(&ui_dir)
                    .map(|mut d| {
                        d.any(|e| {
                            e.map(|e| e.path().extension().map(|ext| ext == "ui").unwrap_or(false))
                                .unwrap_or(false)
                        })
                    })
                    .unwrap_or(false);
                if !has_ui {
                    // Not an error, just if empty
                }
            }
        }
    }

    // Check web files if present — ensure they include qwebchannel.js reference
    let web_candidates = vec![
        base.join("web"),
        base.join(base.file_name().unwrap_or_default()).join("web"),
    ];
    for web_dir in web_candidates {
        if web_dir.exists() {
            if let Ok(entries) = std::fs::read_dir(&web_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.extension().map(|e| e == "html").unwrap_or(false) {
                        if let Ok(content) = std::fs::read_to_string(&path) {
                            if !content.contains("qwebchannel") && !content.contains("QWebChannel")
                            {
                                errors.push(format!("{} missing qwebchannel.js reference (add <script src=\"qrc:///qtwebchannel/qwebchannel.js\">)", path.display()));
                            }
                        }
                    }
                }
            }
        }
    }

    Ok(errors)
}

// ── UI templates (embedded) ───────────────────────────────────────────────

const MAIN_DIALOG_UI: &str = r#"<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainDialog</class>
 <widget class="QDialog" name="MainDialog">
  <property name="windowTitle"><string>Main Dialog</string></property>
  <layout class="QVBoxLayout" name="verticalLayout">
   <item>
    <layout class="QFormLayout" name="formLayout">
     <item row="0" column="0"><widget class="QLabel" name="label_layer"><property name="text"><string>Input layer</string></property></widget></item>
     <item row="0" column="1"><widget class="QgsMapLayerComboBox" name="input_layer"><property name="filters"><enum>QgsMapLayerProxyModel::VectorLayer</enum></property></widget></item>
     <item row="1" column="0"><widget class="QLabel" name="label_threshold"><property name="text"><string>Threshold</string></property></widget></item>
     <item row="1" column="1"><widget class="QDoubleSpinBox" name="threshold"><property name="minimum"><double>0.0</double></property><property name="maximum"><double>100.0</double></property><property name="value"><double>0.5</double></property></widget></item>
     <item row="2" column="0"><widget class="QLabel" name="label_name"><property name="text"><string>Name</string></property></widget></item>
     <item row="2" column="1"><widget class="QLineEdit" name="name_field"/></item>
    </layout>
   </item>
   <item><widget class="QDialogButtonBox" name="buttonBox"><property name="standardButtons"><set>QDialogButtonBox::Cancel|QDialogButtonBox::Ok</set></property></widget></item>
  </layout>
 </widget>
 <customwidgets><customwidget><class>QgsMapLayerComboBox</class><extends>QComboBox</extends><header>qgsmaplayercombobox.h</header></customwidget></customwidgets>
 <connections><connection><sender>buttonBox</sender><signal>accepted()</signal><receiver>MainDialog</receiver><slot>accept()</slot></connection><connection><sender>buttonBox</sender><signal>rejected()</signal><receiver>MainDialog</receiver><slot>reject()</slot></connection></connections>
</ui>
"#;

const DIALOGS_MAIN_DIALOG_PY: &str = r#"
"""Main dialog — Qt Designer .ui loading pattern (recommended)."""

import os
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import QSettings, Qt

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "..", "ui", "main_dialog.ui")
)

class MainDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("Main Dialog")
        self._restore_settings()
        self.buttonBox.accepted.connect(self._on_accepted)

    def _restore_settings(self):
        s = QSettings()
        self.name_field.setText(s.value("{name}/main_dialog/name", "", type=str))
        self.threshold.setValue(s.value("{name}/main_dialog/threshold", 0.5, type=float))

    def _on_accepted(self):
        s = QSettings()
        s.setValue("{name}/main_dialog/name", self.name_field.text())
        s.setValue("{name}/main_dialog/threshold", self.threshold.value())

    def get_values(self):
        return {
            "input_layer": self.input_layer.currentLayer() if hasattr(self.input_layer, "currentLayer") else None,
            "threshold": self.threshold.value(),
            "name": self.name_field.text(),
        }

try:
    from qgis_sdk.ui import Dialog, field, layout, Button, dialog

    @dialog(title="Main Dialog", persist=True)
    def make_declarative_dialog():
        return [
            field.layer("input_layer", label="Input layer"),
            field.spin("threshold", label="Threshold", default=0.5, min=0.0, max=100.0),
            field.text("name", label="Name"),
        ]
except ImportError:
    make_declarative_dialog = None
"#;

const WEB_MAP_HTML: &str = r#"<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>QGIS Web View</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>html,body{height:100%;margin:0} #map{height:85%} #info{padding:8px;background:#f5f5f5}</style>
</head>
<body>
<div id="info"><strong id="layer-name">Loading...</strong> <button onclick="sendToPython()">Send to Python</button></div>
<div id="map"></div>
<script>
var bridge=null;
var map=L.map('map').setView([51.505,-0.09],13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
new QWebChannel(qt.webChannelTransport,function(channel){
  bridge=channel.objects.bridge;
  if(bridge){bridge.get_layer(function(r){try{var d=typeof r==='string'?JSON.parse(r):r;document.getElementById('layer-name').innerText="Layer: "+d.name}catch(e){document.getElementById('layer-name').innerText=r}})}
});
function sendToPython(){if(bridge&&bridge.log){bridge.log("Hello from JS")}}
function updateFromPython(data){console.log("From Python:",data); var info=typeof data==='string'?JSON.parse(data):data; if(info.center){map.setView(info.center,info.zoom||13)}}
</script>
</body>
</html>
"#;

const DIALOGS_WEB_DIALOG_PY: &str = r#"
"""Web dialog — QWebEngineView + QWebChannel bridge."""

from pathlib import Path
from qgis_sdk.ui import WebDialog

HTML_FILE = Path(__file__).parent.parent / "web" / "map.html"

class MapBridge:
    def get_layer(self):
        import json
        return json.dumps({"name": "buildings", "count": 100})
    def log(self, msg):
        print(f"[JS] {msg}")
        return "ok"

def show_web_dialog(parent=None):
    dlg = WebDialog.from_file(HTML_FILE, title="Map View", width=900, height=700, parent=parent)
    dlg.set_bridge(MapBridge())
    return dlg.exec()

try:
    from qgis_sdk.ui import web_bridge
    web_dlg = WebDialog.from_file(HTML_FILE, title="Map View", width=900, height=700)
    @web_bridge(web_dlg)
    class Bridge:
        def get_layer(self):
            return {"name": "buildings", "count": 100}
        def get_extent(self):
            return {"xmin": -180, "ymin": -90, "xmax": 180, "ymax": 90}
except ImportError:
    web_dlg = None
    Bridge = None
"#;

#[pyfunction]
#[pyo3(signature = (name, path, plugin_type="general", with_rust=false, with_web=false, with_ui=true))]
fn scaffold_plugin(
    name: &str,
    path: &str,
    plugin_type: &str,
    with_rust: bool,
    with_web: bool,
    with_ui: bool,
) -> PyResult<String> {
    let base = PathBuf::from(path).join(name);

    if base.exists() {
        return Err(PyValueError::new_err(format!(
            "directory already exists: {}",
            base.display()
        )));
    }

    std::fs::create_dir_all(&base).map_err(|e| PyValueError::new_err(e.to_string()))?;
    std::fs::create_dir_all(base.join(name)).map_err(|e| PyValueError::new_err(e.to_string()))?;

    let class_name = to_pascal_case(name);

    // __init__.py
    let init_py = if with_web {
        format!(
            r#"""{name} — QGIS plugin with UI + WebEngine."""

from qgis_sdk import Plugin, action, toolbar

class {class_name}Plugin(Plugin):
    name = "{name}"
    version = "0.1.0"
    description = "Does useful things — with dialogs and web view"
    author = "Your Name"
    email = "you@example.com"
    qgis_min_version = "3.28"
    category = "Vector"

    @toolbar("{name} Toolbar")
    @action(tooltip="Run {name}")
    def run(self, iface):
        try:
            from .dialogs.main_dialog import MainDialog
            dlg = MainDialog(parent=iface.mainWindow())
            if dlg.exec() == MainDialog.Accepted:
                vals = dlg.get_values()
                iface.messageBar().pushMessage(f"{name}: {{vals}}")
        except Exception:
            try:
                from .dialogs.main_dialog import make_declarative_dialog
                if make_declarative_dialog:
                    dlg = make_declarative_dialog()
                    if dlg.exec() == 1:
                        iface.messageBar().pushMessage("Hello from {name}! (declarative)")
                else:
                    iface.messageBar().pushMessage("Hello from {name}!")
            except Exception:
                iface.messageBar().pushMessage("Hello from {name}!")

    @toolbar("{name} Toolbar")
    @action(tooltip="Open web map")
    def open_web(self, iface):
        try:
            from .dialogs.web_dialog import show_web_dialog
            show_web_dialog(parent=iface.mainWindow())
        except Exception as e:
            iface.messageBar().pushMessage(f"Web view requires QWebEngine: {{e}}")

def classFactory(iface):
    return {class_name}Plugin(iface)
"#,
            name = name,
            class_name = class_name,
        )
    } else {
        format!(
            r#"""{name} — QGIS plugin with UI dialogs."""

from qgis_sdk import Plugin, action, toolbar

class {class_name}Plugin(Plugin):
    name = "{name}"
    version = "0.1.0"
    description = "Does useful things — with dialogs"
    author = "Your Name"
    email = "you@example.com"
    qgis_min_version = "3.28"
    category = "Vector"

    @toolbar("{name} Toolbar")
    @action(tooltip="Run {name}")
    def run(self, iface):
        try:
            from .dialogs.main_dialog import MainDialog
            dlg = MainDialog(parent=iface.mainWindow())
            if dlg.exec() == MainDialog.Accepted:
                vals = dlg.get_values()
                iface.messageBar().pushMessage(f"{name}: {{vals}}")
        except Exception:
            try:
                from .dialogs.main_dialog import make_declarative_dialog
                if make_declarative_dialog:
                    dlg = make_declarative_dialog()
                    if dlg.exec() == 1:
                        iface.messageBar().pushMessage("Hello from {name}! (declarative)")
                else:
                    iface.messageBar().pushMessage("Hello from {name}!")
            except Exception:
                iface.messageBar().pushMessage("Hello from {name}!")

def classFactory(iface):
    return {class_name}Plugin(iface)
"#,
            name = name,
            class_name = class_name,
        )
    };

    std::fs::write(base.join(name).join("__init__.py"), init_py)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;

    // dialogs + ui
    if with_ui {
        let dialogs_dir = base.join(name).join("dialogs");
        std::fs::create_dir_all(&dialogs_dir).map_err(|e| PyValueError::new_err(e.to_string()))?;
        std::fs::write(
            dialogs_dir.join("__init__.py"),
            "from .main_dialog import MainDialog, make_declarative_dialog\n",
        )
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let dialog_py = DIALOGS_MAIN_DIALOG_PY.replace("{name}", name);
        std::fs::write(dialogs_dir.join("main_dialog.py"), dialog_py)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;

        if with_web {
            std::fs::write(dialogs_dir.join("web_dialog.py"), DIALOGS_WEB_DIALOG_PY)
                .map_err(|e| PyValueError::new_err(e.to_string()))?;
        }

        let ui_dir = base.join(name).join("ui");
        std::fs::create_dir_all(&ui_dir).map_err(|e| PyValueError::new_err(e.to_string()))?;
        std::fs::write(ui_dir.join("__init__.py"), "")
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        std::fs::write(ui_dir.join("main_dialog.ui"), MAIN_DIALOG_UI)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;

        let icons_dir = base.join(name).join("icons");
        std::fs::create_dir_all(&icons_dir).map_err(|e| PyValueError::new_err(e.to_string()))?;
        std::fs::write(icons_dir.join(".gitkeep"), "")
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
    }

    if with_web {
        let web_dir = base.join(name).join("web");
        std::fs::create_dir_all(&web_dir).map_err(|e| PyValueError::new_err(e.to_string()))?;
        std::fs::write(web_dir.join("__init__.py"), "")
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        std::fs::write(web_dir.join("map.html"), WEB_MAP_HTML)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
    }

    let metadata = format!(
        r#"[general]
name={name}
qgisMinimumVersion=3.28
description=Does useful things
about=Does useful things
version=0.1.0
author=Your Name
email=you@example.com
category=Vector
hasProcessingProvider={}
"#,
        if plugin_type == "processing" {
            "True"
        } else {
            "False"
        },
        name = name,
    );

    std::fs::write(base.join("metadata.txt"), metadata)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;

    let readme = if with_web {
        format!(
            r#"# {name}

QGIS plugin built with qgis-sdk — with UI dialogs and WebEngine map.

## Features

- **Dialogs via PyQt**: `dialogs/main_dialog.py` loads `ui/main_dialog.ui` via `uic.loadUiType`
- **WebEngine HTML**: `web/map.html` with Leaflet + QWebChannel bridge (`qrc:///qtwebchannel/qwebchannel.js`)
- **Declarative fallback**: `qgis_sdk.ui.Dialog` / `WebDialog` for testing without QGIS

## Development

```bash
pip install qgis-sdk
python -m pytest
qgis-plugin install
qgis-plugin dev
qgis-plugin package
```
"#,
        )
    } else {
        format!(
            r#"# {name}

QGIS plugin built with qgis-sdk — with UI dialogs.

## Development

```bash
pip install qgis-sdk
python -m pytest
qgis-plugin install
qgis-plugin dev
qgis-plugin package
```
"#,
        )
    };

    std::fs::write(base.join("README.md"), readme)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;

    let pyproject = format!(
        r#"[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{name}"
version = "0.1.0"
description = "QGIS plugin {name}"
readme = "README.md"
requires-python = ">=3.11"
dependencies = ["qgis-sdk"]

[tool.hatch.build.targets.wheel]
packages = ["{name}"]
include = [
    "{name}/ui/*.ui",
    "{name}/web/*.html",
    "{name}/icons/*",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
"#
    );
    std::fs::write(base.join("pyproject.toml"), pyproject)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;

    // tests
    let tests_dir = base.join("tests");
    std::fs::create_dir_all(&tests_dir).map_err(|e| PyValueError::new_err(e.to_string()))?;
    std::fs::write(tests_dir.join("__init__.py"), "")
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    let test_dialog = format!(
        r#"""Test dialog logic without QGIS/Qt."""

from {name}.dialogs.main_dialog import make_declarative_dialog

def test_dialog_defaults():
    if make_declarative_dialog is None:
        return
    dlg = make_declarative_dialog()
    assert dlg.get("threshold") == 0.5
    assert dlg.title == "Main Dialog"

def test_dialog_exec():
    if make_declarative_dialog is None:
        return
    dlg = make_declarative_dialog()
    result = dlg.exec()
    assert result == 1
"#,
    );
    std::fs::write(tests_dir.join("test_dialog.py"), test_dialog)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;

    if with_rust {
        let cargo_toml = format!(
            r#"[package]
name = "{name}"
version = "0.1.0"
edition = "2021"

[lib]
name = "_native"
crate-type = ["cdylib"]

[dependencies]
pyo3 = {{ version = "0.22", features = ["extension-module"] }}
"#,
        );
        std::fs::write(base.join("Cargo.toml"), cargo_toml)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;

        std::fs::create_dir_all(base.join("src"))
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        std::fs::write(
            base.join("src").join("lib.rs"),
            r#"use pyo3::prelude::*;

#[pyfunction]
fn hello() -> &'static str {
    "Hello from Rust!"
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello, m)?)?;
    Ok(())
}
"#,
        )
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    }

    Ok(base.display().to_string())
}

fn to_pascal_case(s: &str) -> String {
    s.split(['_', '-', ' '])
        .filter(|part| !part.is_empty())
        .map(|part| {
            let mut chars = part.chars();
            match chars.next() {
                None => String::new(),
                Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
            }
        })
        .collect()
}

#[pyfunction]
fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

// ── Module definition ───────────────────────────────────────────────────────

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyMetadataField>()?;
    m.add_function(wrap_pyfunction!(metadata_fields, m)?)?;
    m.add_function(wrap_pyfunction!(render_metadata_from_dict, m)?)?;
    m.add_function(wrap_pyfunction!(validate_plugin_structure, m)?)?;
    m.add_function(wrap_pyfunction!(scaffold_plugin, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;

    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}
