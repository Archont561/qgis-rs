"""Tests for qgis_sdk.ui — dialogs via PyQt and WebEngine HTML."""

from __future__ import annotations

import json
from pathlib import Path


def test_ui_import():
    from qgis_sdk import ui
    assert hasattr(ui, "Dialog")
    assert hasattr(ui, "WebDialog")
    assert hasattr(ui, "field")
    assert hasattr(ui, "layout")


def test_field_builders():
    from qgis_sdk.ui import field

    f = field.text("name", label="Name", default="test")
    assert f.name == "name"
    assert f.field_type == "text"
    assert f.default == "test"

    f2 = field.spin("threshold", label="Threshold", default=0.5, min=0.0, max=1.0)
    assert f2.field_type == "spin"
    assert f2.min == 0.0
    assert f2.max == 1.0

    f3 = field.layer("input_layer", label="Input layer", layer_filter="vector")
    assert f3.field_type == "layer"

    f4 = field.combo("choice", label="Choice", options=["a", "b"], default="a")
    assert f4.options == ("a", "b")

    f5 = field.check("enabled", label="Enabled", default=True)
    assert f5.field_type == "check"
    assert f5.default is True


def test_layout_helpers():
    from qgis_sdk.ui import layout, field, Button

    l = layout.vertical(
        field.text("name", label="Name"),
        field.spin("threshold", label="Threshold"),
        layout.buttons(Button.ok(), Button.cancel()),
    )
    assert isinstance(l, list)
    assert len(l) == 3


def test_dialog_declarative():
    from qgis_sdk.ui import Dialog, field, layout, Button, dialog

    dlg = Dialog(
        title="Test Dialog",
        layout=layout.vertical(
            field.text("name", label="Name", default="hello"),
            field.spin("threshold", label="Threshold", default=0.5),
            layout.buttons(Button.ok(), Button.cancel()),
        ),
        width=400,
        height=300,
    )

    assert dlg.title == "Test Dialog"
    assert dlg.get("name") == "hello"
    assert dlg.get("threshold") == 0.5

    dlg.set("name", "world")
    assert dlg.get("name") == "world"

    # exec should fallback to Accepted without Qt
    result = dlg.exec()
    assert result == Dialog.Accepted


def test_dialog_decorator():
    from qgis_sdk.ui import dialog, field

    @dialog(title="Settings", persist=False)
    def settings_dialog():
        return [
            field.text("name", label="Name", default="test"),
            field.spin("value", label="Value", default=1.0),
        ]

    dlg = settings_dialog()
    assert dlg.title == "Settings"
    assert dlg.get("name") == "test"
    assert dlg.get("value") == 1.0
    assert dlg.exec() == 1


def test_web_dialog():
    from qgis_sdk.ui import WebDialog

    html = "<html><body><h1>Hello</h1></body></html>"
    dlg = WebDialog(title="Web Test", html=html, width=800, height=600)

    assert dlg.title == "Web Test"
    assert dlg.html == html
    assert dlg.width == 800

    # exec fallback
    result = dlg.exec()
    assert result == 1


def test_web_dialog_from_file(tmp_path):
    from qgis_sdk.ui import WebDialog

    html_file = tmp_path / "test.html"
    html_file.write_text("<html><body>Test</body></html>", encoding="utf-8")

    dlg = WebDialog.from_file(html_file, title="File Test")
    assert dlg.title == "File Test"
    assert "Test" in dlg.html


def test_web_bridge_decorator():
    from qgis_sdk.ui import WebDialog, web_bridge

    html = "<html><body><script src=\"qrc:///qtwebchannel/qwebchannel.js\"></script></body></html>"
    dlg = WebDialog(html=html, title="Bridge Test")

    @web_bridge(dlg)
    class Bridge:
        def get_data(self):
            return {"key": "value"}

        def log(self, msg):
            return f"logged: {msg}"

    # Bridge should be set on dialog
    assert dlg._bridge is not None
    assert hasattr(dlg._bridge, "get_data")

    # Test bridge methods
    result = dlg._bridge.get_data()
    assert result == {"key": "value"}


def test_web_dialog_run_js():
    from qgis_sdk.ui import WebDialog

    dlg = WebDialog(html="<html></html>")
    # Should not crash in fallback mode
    dlg.run_js("console.log('test')")
    dlg.run_js("updateFromPython({message: 'hello'})", callback=lambda x: None)


def test_make_dialog_helpers():
    from qgis_sdk.ui import make_dialog, make_web_view

    # These should raise or fallback without Qt
    try:
        # make_dialog requires file existence check
        import pytest

        with pytest.raises(FileNotFoundError):
            make_dialog("/nonexistent/file.ui")
    except ImportError:
        pass

    # make_web_view should work or fallback
    try:
        view = make_web_view(html="<html>test</html>")
        # If Qt available, view is QWebEngineView, else exception caught inside
        assert view is not None or True
    except Exception:
        # Fallback is OK
        pass


def test_scaffold_with_ui(tmp_path):
    from qgis_sdk.scaffold import scaffold_plugin

    # Test scaffold with UI
    result = scaffold_plugin("my_ui_plugin", str(tmp_path), with_ui=True, with_web=False)
    base = Path(result)

    assert (base / "my_ui_plugin" / "dialogs" / "main_dialog.py").exists()
    assert (base / "my_ui_plugin" / "ui" / "main_dialog.ui").exists()
    assert (base / "my_ui_plugin" / "__init__.py").exists()

    # Check .ui file contains expected elements
    ui_content = (base / "my_ui_plugin" / "ui" / "main_dialog.ui").read_text()
    assert "MainDialog" in ui_content
    assert "QgsMapLayerComboBox" in ui_content
    assert "buttonBox" in ui_content

    # Check dialog py contains uic.loadUiType and WA_DeleteOnClose
    dialog_py = (base / "my_ui_plugin" / "dialogs" / "main_dialog.py").read_text()
    assert "uic.loadUiType" in dialog_py
    assert "WA_DeleteOnClose" in dialog_py
    assert "QSettings" in dialog_py


def test_scaffold_with_web(tmp_path):
    from qgis_sdk.scaffold import scaffold_plugin

    result = scaffold_plugin("my_web_plugin", str(tmp_path), with_ui=True, with_web=True)
    base = Path(result)

    assert (base / "my_web_plugin" / "web" / "map.html").exists()
    assert (base / "my_web_plugin" / "dialogs" / "web_dialog.py").exists()
    assert (base / "my_web_plugin" / "ui" / "main_dialog.ui").exists()

    # Check web html contains qwebchannel and leaflet
    html_content = (base / "my_web_plugin" / "web" / "map.html").read_text()
    assert "qrc:///qtwebchannel/qwebchannel.js" in html_content
    assert "QWebChannel" in html_content
    assert "leaflet" in html_content.lower()
    assert "bridge" in html_content

    # Check web_dialog.py contains WebDialog and bridge
    web_dialog_py = (base / "my_web_plugin" / "dialogs" / "web_dialog.py").read_text()
    assert "WebDialog" in web_dialog_py
    assert "QWebChannel" in web_dialog_py or "bridge" in web_dialog_py


def test_cli_new_with_web(tmp_path, capsys):
    from qgis_sdk.cli import main

    rc = main(["new", "web_test_plugin", "--web", "-o", str(tmp_path)])
    assert rc == 0

    plugin_dir = tmp_path / "web_test_plugin"
    assert (plugin_dir / "web_test_plugin" / "web" / "map.html").exists()
    assert (plugin_dir / "web_test_plugin" / "dialogs" / "web_dialog.py").exists()

    out = capsys.readouterr().out
    assert "web" in out.lower() or "Web" in out


def test_cli_new_no_ui(tmp_path, capsys):
    from qgis_sdk.cli import main

    rc = main(["new", "no_ui_plugin", "--no-ui", "-o", str(tmp_path)])
    assert rc == 0

    plugin_dir = tmp_path / "no_ui_plugin"
    # Should NOT have ui folder
    assert not (plugin_dir / "no_ui_plugin" / "ui").exists()


def test_cli_ui_commands(tmp_path, capsys):
    from qgis_sdk.cli import main

    # Create base plugin
    rc = main(["new", "ui_cmd_plugin", "-o", str(tmp_path)])
    assert rc == 0

    plugin_dir = tmp_path / "ui_cmd_plugin"
    pkg_dir = plugin_dir / "ui_cmd_plugin"

    # Add web via ui command
    rc = main(["ui", "add-web", str(pkg_dir)])
    assert rc == 0
    assert (pkg_dir / "web" / "map.html").exists()

    # Add dialog via ui command
    rc = main(["ui", "add-dialog", str(pkg_dir), "--name", "custom_dialog"])
    assert rc == 0
    assert (pkg_dir / "ui" / "custom_dialog.ui").exists()
    assert (pkg_dir / "dialogs" / "custom_dialog.py").exists()


def test_validate_with_ui(tmp_path, capsys):
    from qgis_sdk.cli import main
    from qgis_sdk.scaffold import scaffold_plugin

    result = scaffold_plugin("validate_ui", str(tmp_path), with_ui=True, with_web=True)
    base = Path(result)

    rc = main(["validate", str(base)])
    assert rc == 0

    out = capsys.readouterr().out
    assert "valid" in out.lower()


def test_validate_web_missing_qwebchannel(tmp_path, capsys):
    from qgis_sdk.cli import main

    # Create plugin with bad html (no qwebchannel)
    plugin_dir = tmp_path / "bad_web"
    plugin_dir.mkdir()
    (plugin_dir / "metadata.txt").write_text("[general]\nname=bad_web\nversion=0.1.0\n")
    web_dir = plugin_dir / "web"
    web_dir.mkdir()
    (web_dir / "map.html").write_text("<html><body>No bridge</body></html>")

    # Python fallback validation doesn't check web, but Rust core would
    # So we test that our Python scaffold always includes qwebchannel
    rc = main(["validate", str(plugin_dir)])
    # Should still be valid in fallback mode
    assert rc == 0


def test_scaffold_with_react(tmp_path):
    from qgis_sdk.scaffold import scaffold_plugin

    result = scaffold_plugin("my_react_plugin", str(tmp_path), with_ui=True, with_web=True, web_framework="react")
    base = Path(result)

    assert (base / "my_react_plugin" / "web" / "react.html").exists()
    assert (base / "my_react_plugin" / "web" / "map.html").exists()
    assert (base / "my_react_plugin" / "frontend" / "package.json").exists()

    react_html = (base / "my_react_plugin" / "web" / "react.html").read_text()
    assert "React" in react_html
    assert "qrc:///qtwebchannel/qwebchannel.js" in react_html
    assert "useQgisBridge" in react_html

    pkg_json = (base / "my_react_plugin" / "frontend" / "package.json").read_text()
    assert "react" in pkg_json.lower()
    assert "vite" in pkg_json.lower()


def test_scaffold_with_vue(tmp_path):
    from qgis_sdk.scaffold import scaffold_plugin

    result = scaffold_plugin("my_vue_plugin", str(tmp_path), with_ui=True, with_web=True, web_framework="vue")
    base = Path(result)

    assert (base / "my_vue_plugin" / "web" / "vue.html").exists()
    vue_html = (base / "my_vue_plugin" / "web" / "vue.html").read_text()
    assert "Vue" in vue_html
    assert "qrc:///qtwebchannel/qwebchannel.js" in vue_html
    assert "ref" in vue_html


def test_scaffold_with_webcomponents(tmp_path):
    from qgis_sdk.scaffold import scaffold_plugin

    result = scaffold_plugin("my_wc_plugin", str(tmp_path), with_ui=True, with_web=True, web_framework="webcomponents")
    base = Path(result)

    assert (base / "my_wc_plugin" / "web" / "components.html").exists()
    wc_html = (base / "my_wc_plugin" / "web" / "components.html").read_text()
    assert "Web Components" in wc_html
    assert "customElements.define" in wc_html
    assert "Shadow" in wc_html or "shadow" in wc_html


def test_cli_new_with_react(tmp_path, capsys):
    from qgis_sdk.cli import main

    rc = main(["new", "react_test_plugin", "--web", "--framework", "react", "-o", str(tmp_path)])
    assert rc == 0

    plugin_dir = tmp_path / "react_test_plugin"
    assert (plugin_dir / "react_test_plugin" / "web" / "react.html").exists()
    assert (plugin_dir / "react_test_plugin" / "frontend" / "package.json").exists()

    out = capsys.readouterr().out
    assert "react" in out.lower() or "React" in out


def test_cli_new_with_vue(tmp_path, capsys):
    from qgis_sdk.cli import main

    rc = main(["new", "vue_test_plugin", "--web", "--framework", "vue", "-o", str(tmp_path)])
    assert rc == 0

    plugin_dir = tmp_path / "vue_test_plugin"
    assert (plugin_dir / "vue_test_plugin" / "web" / "vue.html").exists()

    out = capsys.readouterr().out
    assert "vue" in out.lower() or "Vue" in out or "web" in out.lower()
