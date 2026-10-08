"""QGIS-free behavior tests for the built-in QGIS API's host discovery."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest

from qgis_sdk.bridge.qgis_api import QgisApi


class _FakeLayer:
    def __init__(self, layer_id: str, name: str):
        self._id = layer_id
        self._name = name

    def id(self) -> str:
        return self._id

    def name(self) -> str:
        return self._name


class _FakeIface:
    def __init__(self, layer_id: str, name: str):
        self.layer = _FakeLayer(layer_id, name)
        self.active_layer_calls = 0

    def activeLayer(self) -> _FakeLayer:
        self.active_layer_calls += 1
        return self.layer


class _FakeProject:
    def fileName(self) -> str:
        return "/tmp/project.qgz"

    def crs(self):
        return type("FakeCrs", (), {"authid": lambda self: "EPSG:4326"})()

    def title(self) -> str:
        return "Fake project"


class _TrackingModule(ModuleType):
    def __init__(self, name: str, tracked_member: str, lookups: list[str]):
        super().__init__(name)
        self._tracked_member = tracked_member
        self._lookups = lookups

    def __getattribute__(self, name: str):
        if name == ModuleType.__getattribute__(self, "_tracked_member"):
            ModuleType.__getattribute__(self, "_lookups").append(name)
        return ModuleType.__getattribute__(self, name)


def _install_qgis_modules(
    monkeypatch,
    *,
    iface=None,
    core_members: dict[str, Any] | None = None,
    lookups: list[str] | None = None,
):
    """Install tiny QGIS module fakes so host calls never need a QGIS runtime."""
    qgis = ModuleType("qgis")
    qgis.__path__ = []
    utils = (
        _TrackingModule("qgis.utils", "iface", lookups)
        if lookups is not None
        else ModuleType("qgis.utils")
    )
    utils.iface = iface
    core = ModuleType("qgis.core")
    for name, value in (core_members or {}).items():
        setattr(core, name, value)
    qgis.utils = utils
    qgis.core = core

    monkeypatch.setitem(sys.modules, "qgis", qgis)
    monkeypatch.setitem(sys.modules, "qgis.utils", utils)
    monkeypatch.setitem(sys.modules, "qgis.core", core)


def test_explicit_iface_injection_precedes_qgis_global(monkeypatch):
    injected = _FakeIface("injected-id", "Injected layer")
    discovered = _FakeIface("global-id", "Global layer")
    _install_qgis_modules(monkeypatch, iface=discovered)

    api = QgisApi(iface=injected)

    assert api.iface_active_layer() == {"id": "injected-id", "name": "Injected layer"}
    assert injected.active_layer_calls == 1
    assert discovered.active_layer_calls == 0


def test_falsey_explicit_iface_still_overrides_qgis_global(monkeypatch):
    class FalseyIface:
        def __bool__(self):
            return False

    discovered = _FakeIface("global-id", "Global layer")
    _install_qgis_modules(monkeypatch, iface=discovered)

    api = QgisApi(iface=FalseyIface())

    assert api.iface_active_layer() is None
    assert discovered.active_layer_calls == 0


def test_qgis_iface_discovery_is_lazy_until_a_host_call(monkeypatch):
    lookups = []
    discovered = _FakeIface("global-id", "Global layer")
    _install_qgis_modules(monkeypatch, iface=discovered, lookups=lookups)

    api = QgisApi()

    assert lookups == []
    assert api.layers_active() == {"id": "global-id", "name": "Global layer"}
    assert "iface" in lookups


def test_qgis_free_host_calls_keep_fallbacks_when_qgis_is_unavailable(monkeypatch, capsys):
    for module_name in ("qgis", "qgis.utils", "qgis.core"):
        monkeypatch.setitem(sys.modules, module_name, None)

    api = QgisApi()

    assert api.iface_zoom_to_layer("layer-id") is False
    assert api.iface_active_layer() is None
    assert api.iface_show_message("fallback", "iface message") is True
    assert api.layers_list() == []
    assert api.layers_active() is None
    assert api.layers_remove("layer-id") is False
    assert api.layers_zoom_to("layer-id") is False
    assert api.layers_set_active("layer-id") is False
    assert api.layers_get("layer-id") is None
    assert api.project_info() == {"path": "", "crs": "", "title": ""}
    assert api.project_write() is False
    assert api.project_crs() == ""
    assert api.project_set_crs("EPSG:4326") is False
    assert api.project_path() == ""
    assert api.message_info("fallback", "message") is True

    with pytest.raises(RuntimeError, match="QGIS not available"):
        api.layers_add_vector("missing.shp")
    with pytest.raises(RuntimeError, match="QGIS not available"):
        api.layers_add_raster("missing.tif")

    output = capsys.readouterr().out
    assert "[Iface] fallback: iface message" in output
    assert "[Message] fallback: message" in output


def test_project_host_call_uses_qgis_project_instance(monkeypatch):
    project = _FakeProject()
    instances = []

    class FakeQgsProject:
        @staticmethod
        def instance():
            instances.append(project)
            return project

    _install_qgis_modules(monkeypatch, core_members={"QgsProject": FakeQgsProject})

    api = QgisApi()

    assert api.project_info() == {
        "path": "/tmp/project.qgz",
        "crs": "EPSG:4326",
        "title": "Fake project",
    }
    assert instances == [project]


@pytest.mark.parametrize("failure_type", [ImportError, RuntimeError])
def test_project_host_call_preserves_project_instance_exception_behavior(
    monkeypatch, failure_type
):
    class FakeQgsProject:
        @staticmethod
        def instance():
            raise failure_type("project instance failed")

    _install_qgis_modules(monkeypatch, core_members={"QgsProject": FakeQgsProject})
    api = QgisApi()

    if failure_type is ImportError:
        assert api.project_info() == {"path": "", "crs": "", "title": ""}
    else:
        with pytest.raises(RuntimeError, match="project instance failed"):
            api.project_info()
