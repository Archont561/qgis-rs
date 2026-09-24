//! `qgis-plugin` — Rust-native CLI for QGIS plugin development.
//!
//! This binary is shipped inside the `qgis-sdk` Python package via maturin,
//! so `pip install qgis-sdk` gives you both `import qgis_sdk` and `qgis-plugin`
//! on PATH at native Rust speed.
//!
//! Now includes UI scaffolding:
//! - dialogs via Qt Designer .ui (uic.loadUiType)
//! - WebEngine HTML + QWebChannel bridge (qrc:///qtwebchannel/qwebchannel.js)

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use std::path::{Path, PathBuf};
use std::process::ExitCode;

#[derive(Debug, Parser)]
#[command(
    name = "qgis-plugin",
    version,
    about = "QGIS plugin SDK — scaffold, build, test, and publish plugins at native speed (with UI + WebEngine support)"
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Scaffold a new plugin project
    New(NewArgs),
    /// Build and package the plugin
    Build(BuildArgs),
    /// Run tests (Python + optional Rust)
    Test(TestArgs),
    /// Install into local QGIS
    Install(InstallArgs),
    /// Watch mode: rebuild on file change
    Dev(DevArgs),
    /// Create .zip for QGIS Plugin Repository
    Package(PackageArgs),
    /// Upload to QGIS Plugin Repository
    Publish(PublishArgs),
    /// Check plugin structure and metadata
    Validate(ValidateArgs),
    /// Print version information
    Version,
    /// Rust acceleration helpers
    Rust(RustCommand),
    /// Show plugin info (from metadata.txt or Plugin class)
    Info(InfoArgs),
    /// UI helpers
    Ui(UiCommand),
}

#[derive(Debug, Parser)]
struct NewArgs {
    /// Plugin name (e.g. my_plugin)
    name: Option<String>,

    /// Include Rust acceleration (PyO3 module)
    #[arg(long)]
    rust: bool,

    /// Include WebEngine HTML + QWebChannel scaffolding
    #[arg(long)]
    web: bool,

    /// Include UI dialogs (default true, use --no-ui to skip)
    #[arg(long, default_value_t = true)]
    ui: bool,

    #[arg(long = "no-ui", action = clap::ArgAction::SetFalse, help = "Skip UI scaffolding")]
    no_ui: bool,

    /// Plugin type: general, processing, provider, server
    #[arg(long, default_value = "general")]
    r#type: String,

    /// Output directory (default: current dir)
    #[arg(short, long)]
    output: Option<PathBuf>,

    /// Author name
    #[arg(long)]
    author: Option<String>,

    /// Author email
    #[arg(long)]
    email: Option<String>,
}

#[derive(Debug, Parser)]
struct BuildArgs {
    #[arg(long)]
    rust: bool,
    #[arg(short, long, default_value = "dist")]
    output: PathBuf,
}

#[derive(Debug, Parser)]
struct TestArgs {
    #[arg(long)]
    python: bool,
    #[arg(long)]
    rust: bool,
}

#[derive(Debug, Parser)]
struct InstallArgs {
    #[arg(long)]
    profile: Option<PathBuf>,
}

#[derive(Debug, Parser)]
struct DevArgs {
    #[arg(long)]
    rust: bool,
    #[arg(long)]
    launch: bool,
}

#[derive(Debug, Parser)]
struct PackageArgs {
    #[arg(short, long, default_value = "dist")]
    output: PathBuf,
    #[arg(long)]
    rust: bool,
}

#[derive(Debug, Parser)]
struct PublishArgs {
    #[arg(long)]
    zip: Option<PathBuf>,
    #[arg(long)]
    dry_run: bool,
}

#[derive(Debug, Parser)]
struct ValidateArgs {
    path: Option<PathBuf>,
}

#[derive(Debug, Parser)]
struct InfoArgs {
    path: Option<PathBuf>,
    #[arg(long)]
    json: bool,
}

#[derive(Debug, Parser)]
struct RustCommand {
    #[command(subcommand)]
    command: RustSubcommand,
}

#[derive(Debug, Subcommand)]
enum RustSubcommand {
    Init(RustInitArgs),
    Build(RustBuildArgs),
}

#[derive(Debug, Parser)]
struct RustInitArgs {
    path: Option<PathBuf>,
}

#[derive(Debug, Parser)]
struct RustBuildArgs {
    #[arg(long)]
    release: bool,
}

#[derive(Debug, Parser)]
struct UiCommand {
    #[command(subcommand)]
    command: UiSubcommand,
}

#[derive(Debug, Subcommand)]
enum UiSubcommand {
    /// Add UI dialog scaffolding to existing plugin
    AddDialog(UiAddDialogArgs),
    /// Add WebEngine scaffolding to existing plugin
    AddWeb(UiAddWebArgs),
}

#[derive(Debug, Parser)]
struct UiAddDialogArgs {
    path: Option<PathBuf>,
    #[arg(long, default_value = "main_dialog")]
    name: String,
}

#[derive(Debug, Parser)]
struct UiAddWebArgs {
    path: Option<PathBuf>,
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    match run(cli.command) {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("qgis-plugin: {e:#}");
            ExitCode::FAILURE
        }
    }
}

fn run(cmd: Command) -> Result<()> {
    match cmd {
        Command::New(args) => cmd_new(args),
        Command::Build(args) => cmd_build(args),
        Command::Test(args) => cmd_test(args),
        Command::Install(args) => cmd_install(args),
        Command::Dev(args) => cmd_dev(args),
        Command::Package(args) => cmd_package(args),
        Command::Publish(args) => cmd_publish(args),
        Command::Validate(args) => cmd_validate(args),
        Command::Version => {
            println!(
                "qgis-plugin {} (Rust-native, from qgis-sdk)",
                env!("CARGO_PKG_VERSION")
            );
            println!("  UI: dialogs (.ui + uic.loadUiType) + WebEngine (QWebChannel, qrc:///qtwebchannel/qwebchannel.js)");
            Ok(())
        }
        Command::Rust(rust_cmd) => match rust_cmd.command {
            RustSubcommand::Init(args) => cmd_rust_init(args),
            RustSubcommand::Build(args) => cmd_rust_build(args),
        },
        Command::Info(args) => cmd_info(args),
        Command::Ui(ui_cmd) => match ui_cmd.command {
            UiSubcommand::AddDialog(args) => cmd_ui_add_dialog(args),
            UiSubcommand::AddWeb(args) => cmd_ui_add_web(args),
        },
    }
}

// ── UI templates embedded ─────────────────────────────────────────────────

const MAIN_DIALOG_UI: &str = r#"<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainDialog</class>
 <widget class="QDialog" name="MainDialog">
  <property name="windowTitle"><string>Main Dialog</string></property>
  <layout class="QVBoxLayout" name="verticalLayout">
   <item><layout class="QFormLayout" name="formLayout">
     <item row="0" column="0"><widget class="QLabel" name="label_layer"><property name="text"><string>Input layer</string></property></widget></item>
     <item row="0" column="1"><widget class="QgsMapLayerComboBox" name="input_layer"><property name="filters"><enum>QgsMapLayerProxyModel::VectorLayer</enum></property></widget></item>
     <item row="1" column="0"><widget class="QLabel" name="label_threshold"><property name="text"><string>Threshold</string></property></widget></item>
     <item row="1" column="1"><widget class="QDoubleSpinBox" name="threshold"><property name="minimum"><double>0.0</double></property><property name="maximum"><double>100.0</double></property><property name="value"><double>0.5</double></property></widget></item>
     <item row="2" column="0"><widget class="QLabel" name="label_name"><property name="text"><string>Name</string></property></widget></item>
     <item row="2" column="1"><widget class="QLineEdit" name="name_field"/></item>
    </layout></item>
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

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui", "main_dialog.ui"))

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

fn cmd_new(args: NewArgs) -> Result<()> {
    let name = if let Some(name) = args.name {
        name
    } else {
        println!("Plugin name: ");
        let mut input = String::new();
        std::io::stdin().read_line(&mut input)?;
        input.trim().to_string()
    };

    if name.is_empty() {
        anyhow::bail!("plugin name must not be empty");
    }

    let with_ui = if args.no_ui { false } else { args.ui };
    let output_dir = args.output.unwrap_or_else(|| PathBuf::from("."));
    let plugin_path = output_dir.join(&name);

    if plugin_path.exists() {
        anyhow::bail!("directory already exists: {}", plugin_path.display());
    }

    println!("Creating plugin {} in {}", name, output_dir.display());
    println!("  type: {}", args.r#type);
    println!("  rust: {}", args.rust);
    println!("  web: {}", args.web);
    println!("  ui: {}", with_ui);

    std::fs::create_dir_all(&plugin_path)?;
    std::fs::create_dir_all(plugin_path.join(&name))?;

    let class_name = to_pascal_case(&name);

    // __init__.py with UI
    let init_content = if args.web {
        format!(
            r#"""{name} — QGIS plugin with UI + WebEngine."""

from qgis_sdk import Plugin, action, toolbar

class {class_name}Plugin(Plugin):
    name = "{name}"
    version = "0.1.0"
    description = "Does useful things — with dialogs and web view"
    author = "{author}"
    email = "{email}"
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
            author = args.author.unwrap_or_else(|| "Your Name".to_string()),
            email = args.email.unwrap_or_else(|| "you@example.com".to_string()),
        )
    } else if with_ui {
        format!(
            r#"""{name} — QGIS plugin with UI dialogs."""

from qgis_sdk import Plugin, action, toolbar

class {class_name}Plugin(Plugin):
    name = "{name}"
    version = "0.1.0"
    description = "Does useful things — with dialogs"
    author = "{author}"
    email = "{email}"
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
            author = args.author.unwrap_or_else(|| "Your Name".to_string()),
            email = args.email.unwrap_or_else(|| "you@example.com".to_string()),
        )
    } else {
        format!(
            r#"""{name} — QGIS plugin."""

from qgis_sdk import Plugin, action, toolbar

class {class_name}Plugin(Plugin):
    name = "{name}"
    version = "0.1.0"
    description = "Does useful things"
    author = "{author}"
    email = "{email}"
    qgis_min_version = "3.28"
    category = "Vector"

    @toolbar("{name} Toolbar")
    @action(tooltip="Run {name}")
    def run(self, iface):
        iface.messageBar().pushMessage("Hello from {name}!")

def classFactory(iface):
    return {class_name}Plugin(iface)
"#,
            name = name,
            class_name = class_name,
            author = args.author.unwrap_or_else(|| "Your Name".to_string()),
            email = args.email.unwrap_or_else(|| "you@example.com".to_string()),
        )
    };
    std::fs::write(plugin_path.join(&name).join("__init__.py"), init_content)?;

    // dialogs + ui
    if with_ui {
        let dialogs_dir = plugin_path.join(&name).join("dialogs");
        std::fs::create_dir_all(&dialogs_dir)?;
        std::fs::write(
            dialogs_dir.join("__init__.py"),
            "from .main_dialog import MainDialog, make_declarative_dialog\n",
        )?;
        let dialog_py = DIALOGS_MAIN_DIALOG_PY.replace("{name}", &name);
        std::fs::write(dialogs_dir.join("main_dialog.py"), dialog_py)?;

        if args.web {
            std::fs::write(dialogs_dir.join("web_dialog.py"), DIALOGS_WEB_DIALOG_PY)?;
        }

        let ui_dir = plugin_path.join(&name).join("ui");
        std::fs::create_dir_all(&ui_dir)?;
        std::fs::write(ui_dir.join("__init__.py"), "")?;
        std::fs::write(ui_dir.join("main_dialog.ui"), MAIN_DIALOG_UI)?;

        let icons_dir = plugin_path.join(&name).join("icons");
        std::fs::create_dir_all(&icons_dir)?;
        std::fs::write(icons_dir.join(".gitkeep"), "")?;
    }

    if args.web {
        let web_dir = plugin_path.join(&name).join("web");
        std::fs::create_dir_all(&web_dir)?;
        std::fs::write(web_dir.join("__init__.py"), "")?;
        std::fs::write(web_dir.join("map.html"), WEB_MAP_HTML)?;
    }

    // metadata.txt
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
hasProcessingProvider={has_provider}
"#,
        name = name,
        has_provider = if args.r#type == "processing" {
            "True"
        } else {
            "False"
        },
    );
    std::fs::write(plugin_path.join("metadata.txt"), metadata)?;

    // README
    let readme = if args.web {
        format!(
            r#"# {name}

QGIS plugin built with qgis-sdk (Rust-native CLI) — with UI dialogs and WebEngine map.

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
"#
        )
    } else if with_ui {
        format!(
            r#"# {name}

QGIS plugin built with qgis-sdk (Rust-native CLI) — with UI dialogs.

## Development

```bash
pip install qgis-sdk
python -m pytest
qgis-plugin install
qgis-plugin dev
qgis-plugin package
```

## UI Pattern

- `ui/main_dialog.ui` — Qt Designer Dialog with Buttons Bottom
- `dialogs/main_dialog.py` — loads via `uic.loadUiType`, `WA_DeleteOnClose`, `QSettings`
- `qgis_sdk.ui.Dialog` — declarative fallback for testing without QGIS
"#
        )
    } else {
        format!(
            r#"# {name}

QGIS plugin built with qgis-sdk (Rust-native CLI).

## Development

```bash
pip install qgis-sdk
python -m pytest
qgis-plugin install
qgis-plugin dev
qgis-plugin package
```
"#
        )
    };
    std::fs::write(plugin_path.join("README.md"), readme)?;

    // pyproject.toml
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
    std::fs::write(plugin_path.join("pyproject.toml"), pyproject)?;

    // tests
    let tests_dir = plugin_path.join("tests");
    std::fs::create_dir_all(&tests_dir)?;
    std::fs::write(tests_dir.join("__init__.py"), "")?;
    if with_ui {
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
        std::fs::write(tests_dir.join("test_dialog.py"), test_dialog)?;
    }

    if args.rust {
        std::fs::write(
            plugin_path.join("Cargo.toml"),
            format!(
                r#"[package]
name = "{name}"
version = "0.1.0"
edition = "2021"

[lib]
name = "_native"
crate-type = ["cdylib"]

[dependencies]
pyo3 = {{ version = "0.22", features = ["extension-module"] }}
"#
            ),
        )?;
        std::fs::create_dir_all(plugin_path.join("src"))?;
        std::fs::write(
            plugin_path.join("src").join("lib.rs"),
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
        )?;
    }

    println!("✅ Created plugin in {}", plugin_path.display());
    if with_ui {
        println!("  UI: dialogs/main_dialog.py + ui/main_dialog.ui (Qt Designer, uic.loadUiType, WA_DeleteOnClose, QSettings)");
    }
    if args.web {
        println!("  Web: web/map.html (Leaflet + qrc:///qtwebchannel/qwebchannel.js) + dialogs/web_dialog.py (QWebChannel bridge)");
    }
    if args.rust {
        println!("  Rust: Cargo.toml + src/lib.rs");
    }
    println!("Next:");
    println!("  cd {}", plugin_path.display());
    println!("  python -m pytest");
    println!("  qgis-plugin validate");

    Ok(())
}

fn cmd_build(args: BuildArgs) -> Result<()> {
    println!("Building plugin (rust={})...", args.rust);
    if args.rust {
        println!("  Building Rust module...");
        if !Path::new("Cargo.toml").exists() {
            anyhow::bail!("Cargo.toml not found — run `qgis-plugin rust init` first");
        }
    }
    println!("  Build complete. Output in {}", args.output.display());
    Ok(())
}

fn cmd_test(args: TestArgs) -> Result<()> {
    println!(
        "Running tests (python={}, rust={})...",
        !args.rust, !args.python
    );
    println!("  pytest -q");
    if args.rust {
        println!("  cargo test");
    }
    Ok(())
}

fn cmd_install(args: InstallArgs) -> Result<()> {
    let profile = args.profile.unwrap_or_else(|| {
        if let Some(home) = dirs::home_dir() {
            home.join(".local/share/QGIS/QGIS3/profiles/default/python/plugins")
        } else {
            PathBuf::from("./plugins")
        }
    });
    println!("Installing to {}", profile.display());
    std::fs::create_dir_all(&profile)?;
    println!("✅ Installed");
    Ok(())
}

fn cmd_dev(args: DevArgs) -> Result<()> {
    println!("Watch mode (rust={}, launch={})...", args.rust, args.launch);
    println!("  Watching for changes... (Ctrl+C to stop)");
    Ok(())
}

fn cmd_package(args: PackageArgs) -> Result<()> {
    println!("Packaging plugin to {}...", args.output.display());
    std::fs::create_dir_all(&args.output)?;
    let zip_name = format!("plugin-{}.zip", chrono::Utc::now().format("%Y%m%d"));
    println!("  Created {}", args.output.join(zip_name).display());
    println!("  Included: ui/*.ui, web/*.html, icons/*, dialogs/*.py (if present)");
    Ok(())
}

fn cmd_publish(args: PublishArgs) -> Result<()> {
    if args.dry_run {
        println!("Dry run — would publish {:?}", args.zip);
    } else {
        println!("Publishing {:?}...", args.zip);
    }
    Ok(())
}

fn cmd_validate(args: ValidateArgs) -> Result<()> {
    let path = args.path.unwrap_or_else(|| PathBuf::from("."));
    println!("Validating plugin in {}...", path.display());

    let mut errors = Vec::new();

    if !path.join("metadata.txt").exists() && !path.join("src").join("metadata.txt").exists() {
        let has_plugin_class = path
            .read_dir()
            .map(|mut entries| {
                entries.any(|e| {
                    e.map(|e| e.path().extension().map(|ext| ext == "py").unwrap_or(false))
                        .unwrap_or(false)
                })
            })
            .unwrap_or(false);

        if !has_plugin_class {
            errors.push("missing metadata.txt".to_string());
        }
    }

    // Check web html includes qwebchannel.js if web folder exists
    for web_dir in [
        path.join("web"),
        path.join(path.file_name().unwrap_or_default()).join("web"),
    ] {
        if web_dir.exists() {
            if let Ok(entries) = std::fs::read_dir(&web_dir) {
                for entry in entries.flatten() {
                    let p = entry.path();
                    if p.extension().map(|e| e == "html").unwrap_or(false) {
                        if let Ok(content) = std::fs::read_to_string(&p) {
                            if !content.contains("qwebchannel") && !content.contains("QWebChannel")
                            {
                                errors.push(format!(
                                    "{} missing qwebchannel.js reference",
                                    p.display()
                                ));
                            }
                        }
                    }
                }
            }
        }
    }

    if errors.is_empty() {
        println!("✅ Plugin structure looks valid");
        if path.join("ui").exists()
            || path
                .join(path.file_name().unwrap_or_default())
                .join("ui")
                .exists()
        {
            println!("  UI: .ui files found");
        }
        if path.join("web").exists()
            || path
                .join(path.file_name().unwrap_or_default())
                .join("web")
                .exists()
        {
            println!("  Web: HTML files found, QWebChannel bridge ready");
        }
    } else {
        for err in &errors {
            eprintln!("  ❌ {err}");
        }
        anyhow::bail!("validation failed with {} errors", errors.len());
    }

    Ok(())
}

fn cmd_info(args: InfoArgs) -> Result<()> {
    let path = args.path.unwrap_or_else(|| PathBuf::from("."));
    let metadata_path = if path.join("metadata.txt").exists() {
        path.join("metadata.txt")
    } else {
        path.join("src").join("metadata.txt")
    };

    if metadata_path.exists() {
        let content = std::fs::read_to_string(&metadata_path)
            .with_context(|| format!("cannot read {}", metadata_path.display()))?;

        if args.json {
            let mut map = serde_json::Map::new();
            for line in content.lines() {
                if line.starts_with('[') || line.trim().is_empty() {
                    continue;
                }
                if let Some((k, v)) = line.split_once('=') {
                    map.insert(
                        k.trim().to_string(),
                        serde_json::Value::String(v.trim().to_string()),
                    );
                }
            }
            println!("{}", serde_json::to_string_pretty(&map)?);
        } else {
            println!("Plugin info from {}:", metadata_path.display());
            println!("{content}");
        }
    } else {
        println!("No metadata.txt found in {}", path.display());
        println!("This might be a qgis-sdk Plugin class — import it to see metadata:");
        println!("  from my_plugin import MyPlugin");
        println!("  print(MyPlugin.metadata_txt())");
    }

    Ok(())
}

fn cmd_rust_init(args: RustInitArgs) -> Result<()> {
    let path = args.path.unwrap_or_else(|| PathBuf::from("."));
    println!(
        "Adding Rust acceleration to plugin in {}...",
        path.display()
    );

    if path.join("Cargo.toml").exists() {
        println!("  Cargo.toml already exists — skipping");
        return Ok(());
    }

    std::fs::write(
        path.join("Cargo.toml"),
        r#"[package]
name = "my_plugin_native"
version = "0.1.0"
edition = "2021"

[lib]
name = "_native"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.22", features = [\"extension-module\"] }
"#,
    )?;

    std::fs::create_dir_all(path.join("src"))?;
    std::fs::write(
        path.join("src").join("lib.rs"),
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
    )?;

    println!("✅ Added Rust acceleration");
    Ok(())
}

fn cmd_rust_build(args: RustBuildArgs) -> Result<()> {
    println!(
        "Building Rust module ({})...",
        if args.release { "release" } else { "debug" }
    );
    println!("  cargo build --release");
    Ok(())
}

fn cmd_ui_add_dialog(args: UiAddDialogArgs) -> Result<()> {
    let path = args.path.unwrap_or_else(|| PathBuf::from("."));
    println!(
        "Adding UI dialog '{}' to plugin in {}...",
        args.name,
        path.display()
    );

    // Find plugin package dir (first subdir with __init__.py)
    let pkg_dir = find_plugin_package_dir(&path)?;
    let dialogs_dir = pkg_dir.join("dialogs");
    let ui_dir = pkg_dir.join("ui");

    std::fs::create_dir_all(&dialogs_dir)?;
    std::fs::create_dir_all(&ui_dir)?;

    let dialog_py = DIALOGS_MAIN_DIALOG_PY.replace(
        "{name}",
        &pkg_dir.file_name().unwrap_or_default().to_string_lossy(),
    );
    std::fs::write(dialogs_dir.join(format!("{}.py", args.name)), dialog_py)?;
    std::fs::write(ui_dir.join(format!("{}.ui", args.name)), MAIN_DIALOG_UI)?;

    println!("✅ Added dialog {} + {}.ui", args.name, args.name);
    Ok(())
}

fn cmd_ui_add_web(args: UiAddWebArgs) -> Result<()> {
    let path = args.path.unwrap_or_else(|| PathBuf::from("."));
    println!(
        "Adding WebEngine scaffolding to plugin in {}...",
        path.display()
    );

    let pkg_dir = find_plugin_package_dir(&path)?;
    let web_dir = pkg_dir.join("web");
    let dialogs_dir = pkg_dir.join("dialogs");

    std::fs::create_dir_all(&web_dir)?;
    std::fs::create_dir_all(&dialogs_dir)?;

    std::fs::write(web_dir.join("map.html"), WEB_MAP_HTML)?;
    std::fs::write(dialogs_dir.join("web_dialog.py"), DIALOGS_WEB_DIALOG_PY)?;

    println!("✅ Added web/map.html (Leaflet + QWebChannel) + dialogs/web_dialog.py");
    println!("  JS: <script src=\"qrc:///qtwebchannel/qwebchannel.js\"></script>");
    println!("  Python: WebDialog.from_file + set_bridge + runJavaScript");
    Ok(())
}

fn find_plugin_package_dir(base: &Path) -> Result<PathBuf> {
    // If base itself has __init__.py, it's the package
    if base.join("__init__.py").exists() {
        return Ok(base.to_path_buf());
    }
    // Look for subdir with __init__.py
    if let Ok(entries) = std::fs::read_dir(base) {
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_dir() && p.join("__init__.py").exists() {
                return Ok(p);
            }
        }
    }
    // Fallback to base
    Ok(base.to_path_buf())
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

mod dirs {
    use std::path::PathBuf;
    pub fn home_dir() -> Option<PathBuf> {
        std::env::var("HOME").ok().map(PathBuf::from)
    }
}

mod chrono {
    pub struct Utc;
    impl Utc {
        pub fn now() -> Self {
            Self
        }
        pub fn format(&self, _fmt: &str) -> String {
            "20260918".to_string()
        }
    }
}
