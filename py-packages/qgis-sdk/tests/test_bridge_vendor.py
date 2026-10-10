"""Vendored @archont561/qgis-sdk browser bundle: pinning and scaffold linking."""

import hashlib
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
VENDOR_DIR = Path(__file__).resolve().parents[1] / "src" / "qgis_sdk" / "assets" / "bridge"
MANIFEST = VENDOR_DIR / "manifest.json"
BUNDLE_NAME = "qgis-sdk.js"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_vendored_bundle_matches_pinned_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bundle = VENDOR_DIR / BUNDLE_NAME

    assert bundle.is_file()
    assert manifest["file"] == BUNDLE_NAME
    assert manifest["sha256"] == _sha256(bundle)


def test_vendored_bundle_pins_the_typescript_package_version():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    package = json.loads((REPO / "ts-packages" / "qgis-sdk" / "package.json").read_text(encoding="utf-8"))

    assert manifest["package"] == "@archont561/qgis-sdk"
    assert manifest["version"] == package["version"]


def test_scaffold_with_web_links_pinned_bundle(tmp_path):
    from qgis_sdk.scaffold import scaffold_plugin

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    base = Path(scaffold_plugin("bridge_linked", str(tmp_path), with_ui=True, with_web=True))

    copied = base / "bridge_linked" / "web" / BUNDLE_NAME
    assert copied.is_file()
    assert _sha256(copied) == manifest["sha256"]


@pytest.mark.parametrize("with_ui", [True, False])
def test_scaffold_without_web_ships_no_bridge_bundle(tmp_path, with_ui):
    from qgis_sdk.scaffold import scaffold_plugin

    base = Path(scaffold_plugin("bridge_plain", str(tmp_path), with_ui=with_ui, with_web=False))

    assert not list(base.rglob(BUNDLE_NAME))
    assert not (base / "bridge_plain" / "web").exists()


def test_vendored_bundle_publishes_the_webengine_globals():
    bundle = (VENDOR_DIR / BUNDLE_NAME).read_text(encoding="utf-8")

    assert "qgisReady" in bundle
    assert "qgisBridge" in bundle


@pytest.mark.parametrize("framework", ["vanilla", "react", "vue", "webcomponents"])
def test_every_webengine_page_loads_the_vendored_bundle(tmp_path, framework):
    from qgis_sdk.scaffold import scaffold_plugin

    base = Path(
        scaffold_plugin("page_plugin", str(tmp_path), with_ui=True, with_web=True, web_framework=framework)
    )
    pages = sorted((base / "page_plugin" / "web").glob("*.html"))

    assert pages
    for page in pages:
        assert f'src="{BUNDLE_NAME}"' in page.read_text(encoding="utf-8"), page.name
