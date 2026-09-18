"""
qgis_sdk.bootstrap — tiny helper that can be vendored into plugin zip.

No dependencies, works without qgis_sdk installed.
This file is designed to be < 300 LOC, pure-python, single file, copy-pasteable.

Usage in plugin __init__.py:

    try:
        import qgis_sdk
    except ImportError:
        from .bootstrap import ensure_qgis_sdk
        if not ensure_qgis_sdk(auto_install=True, ask_user=True, parent=None):
            def classFactory(iface): return None
            raise

    from qgis_sdk import plugin, toolbar, action
    ...

It tries:
1. extlibs/qgis_sdk (pip --target)
2. vendor/qgis_sdk (fully bundled)
3. pip install --target extlibs
4. offline wheel from wheels/
5. download from PyPI via urllib

For bundling:
    qgis-plugin bootstrap --output my_plugin/bootstrap.py
    qgis-plugin vendor --output my_plugin/vendor
    qgis-plugin package --bundle
"""

from __future__ import annotations

import sys
import pathlib
import subprocess
import zipfile
import urllib.request
import json


def _get_plugin_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent


def _get_extlibs_dir() -> pathlib.Path:
    # When vendored, this file is in plugin root, so parent is plugin dir
    # When installed as qgis_sdk.bootstrap, parent is qgis_sdk package dir
    # We try to find plugin dir by looking for __init__.py or metadata.txt nearby
    # For vendored case, plugin dir is parent of this file
    current = pathlib.Path(__file__).parent
    # If this file is inside qgis_sdk package (installed), plugin dir is not this
    # But for bootstrap logic, we want plugin dir to be parent of this file when vendored
    # So we return parent as plugin dir for vendored, and extlibs inside plugin
    # To handle both, we check if we're inside qgis_sdk package
    if (current / "plugin").exists() or (current.name == "qgis_sdk"):
        # We're inside qgis_sdk package — try to find plugin dir via caller?
        # For installed case, extlibs should be in plugin dir, not here
        # So we try parent.parent if we're in plugin/extlibs/qgis_sdk?
        # Simplify: for installed qgis_sdk, extlibs is sibling of qgis_sdk? No.
        # For vendored, we are in plugin root, so extlibs = plugin/extlibs
        pass
    return current / "extlibs"


def _get_plugin_dir_for_vendored() -> pathlib.Path:
    """When bootstrap.py is vendored into plugin root, plugin dir is its parent."""
    return pathlib.Path(__file__).parent


def _ensure_extlibs_in_path(extlibs: pathlib.Path = None) -> pathlib.Path:
    extlibs = pathlib.Path(extlibs) if extlibs else _get_extlibs_dir()
    # Also check vendored location
    vendored_extlibs = _get_plugin_dir_for_vendored() / "extlibs"
    for p in [extlibs, vendored_extlibs]:
        p_str = str(p)
        if p_str not in sys.path:
            sys.path.insert(0, p_str)
    return extlibs


def is_qgis_sdk_installed() -> bool:
    try:
        import qgis_sdk
        return True
    except ImportError:
        return False


def _find_wheels_dir(plugin_dir: pathlib.Path = None) -> pathlib.Path:
    plugin_dir = plugin_dir or _get_plugin_dir_for_vendored()
    return plugin_dir / "wheels"


def install_from_pip(target_dir=None, auto_confirm=False) -> bool:
    target_dir = pathlib.Path(target_dir or _get_extlibs_dir())
    # Also try vendored extlibs
    vendored_target = _get_plugin_dir_for_vendored() / "extlibs"
    # Use vendored if exists or if target is default
    if target_dir == _get_extlibs_dir() and vendored_target.exists():
        target_dir = vendored_target
    elif target_dir == _get_extlibs_dir():
        # Prefer vendored location for new installs
        target_dir = vendored_target

    target_dir.mkdir(parents=True, exist_ok=True)

    # Try pip
    try:
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "qgis-sdk",
            "--target",
            str(target_dir),
            "--no-deps",
            "--quiet",
        ]
        if auto_confirm:
            cmd.append("--no-input")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return True
        print(f"[qgis-sdk bootstrap] pip install failed: {result.stderr}")
    except Exception as e:
        print(f"[qgis-sdk bootstrap] pip install exception: {e}")

    # Try offline wheel if bundled
    wheels_dir = _find_wheels_dir()
    if wheels_dir.exists():
        for wheel in wheels_dir.glob("qgis_sdk*.whl"):
            try:
                with zipfile.ZipFile(wheel) as z:
                    z.extractall(target_dir)
                print(f"[qgis-sdk bootstrap] installed from wheel {wheel}")
                return True
            except Exception as e:
                print(f"[qgis-sdk bootstrap] wheel install failed {wheel}: {e}")

    # Try download from PyPI via urllib (no pip)
    try:
        with urllib.request.urlopen("https://pypi.org/pypi/qgis-sdk/json", timeout=15) as resp:
            data = json.loads(resp.read().decode())
            # Find wheel url
            for url_info in data.get("urls", []):
                if url_info.get("packagetype") == "bdist_wheel" and "py3" in url_info.get("python_version", ""):
                    wheel_url = url_info["url"]
                    wheel_path = target_dir / "qgis_sdk_tmp.whl"
                    print(f"[qgis-sdk bootstrap] downloading {wheel_url}")
                    urllib.request.urlretrieve(wheel_url, str(wheel_path))
                    with zipfile.ZipFile(wheel_path) as z:
                        z.extractall(target_dir)
                    try:
                        wheel_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    return True
    except Exception as e:
        print(f"[qgis-sdk bootstrap] download failed: {e}")

    return False


def ask_user_to_install(parent=None) -> str:
    try:
        from ._qt import QMessageBox

        msg = QMessageBox(parent)
        msg.setWindowTitle("qgis-sdk required")
        msg.setText(
            "This plugin requires qgis-sdk.\n\n"
            "Install automatically?\n\n"
            "Yes = auto-install via pip to plugin's extlibs (no admin needed)\n"
            "No = show manual instructions"
        )
        try:
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            msg.setDefaultButton(QMessageBox.Yes)
        except Exception:
            pass
        ret = msg.exec() if hasattr(msg, "exec") else msg.exec_()
        if ret == QMessageBox.Yes:
            return "auto"
        elif ret == QMessageBox.No:
            return "manual"
        else:
            return "cancel"
    except Exception:
        # No Qt — console fallback
        print("qgis-sdk required. Install via: pip install qgis-sdk")
        return "manual"


def show_manual_instructions(parent=None):
    try:
        from ._qt import QMessageBox

        QMessageBox.information(
            parent,
            "Install qgis-sdk",
            "Please install qgis-sdk manually:\n\n"
            "pip install qgis-sdk\n"
            "or\n"
            "conda install -c conda-forge qgis-sdk\n\n"
            "Then restart QGIS.\n\n"
            "Docs: https://archont561.github.io/qgis-rs/getting-started/python-sdk/"
        )
    except Exception:
        print("Manual install: pip install qgis-sdk")


def ensure_qgis_sdk(auto_install=True, ask_user=True, parent=None, target_dir=None) -> bool:
    """
    Ensure qgis_sdk is importable. If not, try to install.

    Returns True if qgis_sdk now importable, False otherwise.
    """
    if is_qgis_sdk_installed():
        return True

    # Try extlibs already exists
    _ensure_extlibs_in_path(target_dir)
    if is_qgis_sdk_installed():
        return True

    # Try vendor/ (fully bundled at build time)
    plugin_dir = _get_plugin_dir_for_vendored()
    vendor = plugin_dir / "vendor"
    if vendor.exists() and str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
        if is_qgis_sdk_installed():
            return True

    # Try extlibs in plugin dir explicitly
    extlibs = plugin_dir / "extlibs"
    if extlibs.exists() and str(extlibs) not in sys.path:
        sys.path.insert(0, str(extlibs))
        if is_qgis_sdk_installed():
            return True

    if not auto_install:
        if ask_user:
            show_manual_instructions(parent)
        return False

    if ask_user:
        choice = ask_user_to_install(parent)
        if choice == "cancel":
            return False
        if choice == "manual":
            show_manual_instructions(parent)
            return False

    # Auto install
    extlibs = _get_plugin_dir_for_vendored() / "extlibs"
    _ensure_extlibs_in_path(extlibs)
    success = install_from_pip(target_dir=extlibs, auto_confirm=True)
    if success and is_qgis_sdk_installed():
        return True

    if ask_user:
        show_manual_instructions(parent)
    return False


def get_bootstrap_code() -> str:
    """Return the code of this file for vendoring into plugin."""
    return pathlib.Path(__file__).read_text(encoding="utf-8")


# For convenience when imported as qgis_sdk.bootstrap
def bootstrap_plugin(plugin_dir: pathlib.Path = None) -> bool:
    """Bootstrap for plugin — same as ensure_qgis_sdk but with plugin_dir."""
    plugin_dir = pathlib.Path(plugin_dir) if plugin_dir else _get_plugin_dir_for_vendored()
    extlibs = plugin_dir / "extlibs"
    vendor = plugin_dir / "vendor"

    for p in [extlibs, vendor]:
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))

    if is_qgis_sdk_installed():
        return True

    return ensure_qgis_sdk(auto_install=True, ask_user=True, target_dir=extlibs)
