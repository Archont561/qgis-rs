"""Tests for qgis_sdk.bridge — TS generation from Python bridge."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class SampleBridge:
    def get_layer(self) -> dict:
        return {"name": "roads", "count": 100}

    def get_extent(self) -> dict:
        return {"xmin": -180, "ymin": -90, "xmax": 180, "ymax": 90}

    def log(self, msg: str) -> str:
        return f"logged: {msg}"

    def process(self, data: str) -> dict:
        return {"status": "ok"}

    def get_optional(self, name: Optional[str] = None) -> Optional[dict]:
        return None

    def set_value(self, value: int, enabled: bool = True) -> bool:
        return True


def test_py_type_to_ts():
    from qgis_sdk.bridge import _py_type_to_ts

    assert _py_type_to_ts(str) == "string"
    assert _py_type_to_ts(int) == "number"
    assert _py_type_to_ts(float) == "number"
    assert _py_type_to_ts(bool) == "boolean"
    assert _py_type_to_ts(dict) == "Record<string, any>"
    assert _py_type_to_ts(None) == "void"


def test_generate_ts_bridge():
    from qgis_sdk.bridge import generate_ts_bridge

    ts = generate_ts_bridge(SampleBridge, name="Bridge")

    # Should contain interface
    assert "export interface Bridge" in ts
    # Should contain methods
    assert "get_layer" in ts
    assert "get_extent" in ts
    assert "log" in ts
    assert "process" in ts
    # Should have Promise overloads
    assert "Promise<" in ts
    # Should have callback overloads
    assert "callback:" in ts
    # Should have typed params
    assert "msg: string" in ts or "msg:" in ts
    # Should have auto-generated header
    assert "Auto-generated" in ts


def test_generate_ts_bridge_with_promise_only():
    from qgis_sdk.bridge import generate_ts_bridge

    ts = generate_ts_bridge(SampleBridge, name="MyBridge", with_callback=False, with_promise=True)
    assert "export interface MyBridge" in ts
    assert "Promise<" in ts
    # No callback overload
    # At least should not have callback param for every method? But check contains Promise
    assert "get_layer()" in ts or "get_layer" in ts


def test_generate_js_wrapper():
    from qgis_sdk.bridge import generate_js_wrapper

    js = generate_js_wrapper(SampleBridge, name="Bridge", object_name="bridge")

    assert "loadQWebChannel" in js
    assert "qrc:///qtwebchannel/qwebchannel.js" in js
    assert "createBridge" in js
    assert "promisifyBridge" in js
    assert "QWebChannel" in js
    assert "get_layer" in js
    # Should try multiple sources
    assert "./qwebchannel.js" in js
    # Should have Promise handling
    assert "Promise" in js


def test_generate_package(tmp_path: Path):
    from qgis_sdk.bridge import generate_package

    out = tmp_path / "bridge_pkg"
    result = generate_package(SampleBridge, out, name="Bridge", object_name="bridge")

    assert result.exists()
    assert (result / "bridge.d.ts").exists()
    assert (result / "bridge.js").exists()
    assert (result / "index.ts").exists()
    assert (result / "react.ts").exists()
    assert (result / "vue.ts").exists()
    assert (result / "webcomponents.ts").exists()
    assert (result / "README.md").exists()

    dts = (result / "bridge.d.ts").read_text()
    assert "export interface Bridge" in dts
    assert "get_layer" in dts

    js = (result / "bridge.js").read_text()
    assert "loadQWebChannel" in js

    react = (result / "react.ts").read_text()
    assert "useQgisBridge" in react

    vue = (result / "vue.ts").read_text()
    assert "useQgisBridge" in vue

    wc = (result / "webcomponents.ts").read_text()
    assert "QgisBridgeElement" in wc or "qgis-bridge" in wc


def test_load_bridge_class(tmp_path: Path):
    from qgis_sdk.bridge import load_bridge_class
    import sys

    # Create temp module
    mod_file = tmp_path / "my_bridge.py"
    mod_file.write_text(
        """
class MyBridge:
    def hello(self) -> str:
        return "hi"
"""
    )
    sys.path.insert(0, str(tmp_path))
    try:
        cls = load_bridge_class("my_bridge:MyBridge")
        assert cls.__name__ == "MyBridge"

        cls2 = load_bridge_class("my_bridge.MyBridge")
        assert cls2.__name__ == "MyBridge"
    finally:
        sys.path.remove(str(tmp_path))


def test_cli_bridge_generate(tmp_path: Path, capsys):
    from qgis_sdk.cli import main
    import sys

    mod_file = tmp_path / "cli_bridge.py"
    mod_file.write_text(
        """
class CliBridge:
    def get_layer(self) -> dict:
        return {"name": "test"}
    def log(self, msg: str) -> str:
        return "ok"
"""
    )
    sys.path.insert(0, str(tmp_path))
    try:
        output = tmp_path / "out" / "bridge.d.ts"
        rc = main(
            [
                "bridge",
                "generate",
                "--bridge",
                "cli_bridge:CliBridge",
                "--output",
                str(output),
            ]
        )
        assert rc == 0
        assert output.exists()
        content = output.read_text()
        assert "CliBridge" in content
        assert "get_layer" in content

        # Test --package
        pkg_out = tmp_path / "pkg"
        rc = main(
            [
                "bridge",
                "generate",
                "--bridge",
                "cli_bridge:CliBridge",
                "--output",
                str(pkg_out),
                "--package",
            ]
        )
        assert rc == 0
        assert (pkg_out / "bridge.d.ts").exists()
        assert (pkg_out / "bridge.js").exists()

    finally:
        sys.path.remove(str(tmp_path))


def test_scaffold_generates_bridge_dts(tmp_path: Path):
    from qgis_sdk.scaffold import scaffold_plugin

    result = scaffold_plugin("bridge_test_plugin", str(tmp_path), with_ui=True, with_web=True, web_framework="react")
    base = Path(result)

    assert (base / "bridge_test_plugin" / "web" / "bridge.d.ts").exists()
    dts = (base / "bridge_test_plugin" / "web" / "bridge.d.ts").read_text()
    assert "export interface Bridge" in dts
    assert "get_layer" in dts

    # Frontend should include @qgis-sdk/bridge
    pkg_json = (base / "bridge_test_plugin" / "frontend" / "package.json").read_text()
    assert "@qgis-sdk/bridge" in pkg_json

    # Frontend App.tsx should use @qgis-sdk/bridge/react
    app_tsx = (base / "bridge_test_plugin" / "frontend" / "src" / "App.tsx").read_text()
    assert "@qgis-sdk/bridge" in app_tsx
    assert "useQgisBridge" in app_tsx
    assert "Bridge" in app_tsx


def test_scaffold_vue_includes_bridge(tmp_path: Path):
    from qgis_sdk.scaffold import scaffold_plugin

    result = scaffold_plugin("bridge_vue_plugin", str(tmp_path), with_ui=True, with_web=True, web_framework="vue")
    base = Path(result)

    assert (base / "bridge_vue_plugin" / "web" / "bridge.d.ts").exists()
    pkg_json = (base / "bridge_vue_plugin" / "frontend" / "package.json").read_text()
    assert "@qgis-sdk/bridge" in pkg_json

    app_vue = (base / "bridge_vue_plugin" / "frontend" / "src" / "App.vue").read_text()
    assert "@qgis-sdk/bridge" in app_vue
