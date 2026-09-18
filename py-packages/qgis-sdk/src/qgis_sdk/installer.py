"""qgis_sdk.installer — Installer helper for self-installing runtime.

Provides Installer class that can be used from plugin or CLI.

Usage:
    from qgis_sdk.installer import Installer, ensure_qgis_sdk

    installer = Installer(plugin_dir="/path/to/my_plugin")
    if not installer.is_installed():
        installer.show_dialog()  # Shows QMessageBox with progress

    ensure_qgis_sdk(auto_install=True, ask_user=True)
"""

from __future__ import annotations

import pathlib
import sys
from typing import Optional

from .bootstrap import (
    is_qgis_sdk_installed,
    install_from_pip,
    ask_user_to_install,
    show_manual_instructions,
    ensure_qgis_sdk as bootstrap_ensure,
)


class Installer:
    def __init__(self, plugin_dir: Optional[pathlib.Path] = None):
        self.plugin_dir = pathlib.Path(plugin_dir) if plugin_dir else pathlib.Path(__file__).parent.parent
        # If plugin_dir is actually qgis_sdk package dir, try to find real plugin dir
        # For installed qgis_sdk, plugin_dir should be passed explicitly
        self.extlibs_dir = self.plugin_dir / "extlibs"
        self.vendor_dir = self.plugin_dir / "vendor"
        self.wheels_dir = self.plugin_dir / "wheels"

    def is_installed(self) -> bool:
        return is_qgis_sdk_installed()

    def is_bundled(self) -> bool:
        """Check if vendor/ contains qgis_sdk."""
        return (self.vendor_dir / "qgis_sdk").exists() or (self.vendor_dir / "qgis_sdk" / "__init__.py").exists() or self.vendor_dir.exists()

    def is_offline_wheel_available(self) -> bool:
        if not self.wheels_dir.exists():
            return False
        return any(self.wheels_dir.glob("qgis_sdk*.whl"))

    def install(self, target: str = "extlibs", offline: bool = False) -> bool:
        """Install qgis_sdk.

        Args:
            target: "extlibs" or "vendor" or path
            offline: if True, only use offline wheel, no pip/download
        """
        target_path = pathlib.Path(target) if pathlib.Path(target).is_absolute() else self.plugin_dir / target
        target_path.mkdir(parents=True, exist_ok=True)

        if offline:
            # Only try wheel
            if self.is_offline_wheel_available():
                import zipfile
                for wheel in self.wheels_dir.glob("qgis_sdk*.whl"):
                    try:
                        with zipfile.ZipFile(wheel) as z:
                            z.extractall(target_path)
                        print(f"[Installer] installed from wheel {wheel} to {target_path}")
                        # Add to path
                        if str(target_path) not in sys.path:
                            sys.path.insert(0, str(target_path))
                        return is_qgis_sdk_installed()
                    except Exception as e:
                        print(f"[Installer] wheel install failed {wheel}: {e}")
            return False

        # Normal install via pip/wheel/download
        success = install_from_pip(target_dir=target_path, auto_confirm=True)
        if success:
            if str(target_path) not in sys.path:
                sys.path.insert(0, str(target_path))
        return success and is_qgis_sdk_installed()

    def uninstall(self) -> bool:
        """Remove extlibs."""
        import shutil
        try:
            if self.extlibs_dir.exists():
                shutil.rmtree(self.extlibs_dir)
            return True
        except Exception as e:
            print(f"[Installer] uninstall failed: {e}")
            return False

    def ensure(self, auto_install: bool = True, ask_user: bool = True, parent=None) -> bool:
        return bootstrap_ensure(auto_install=auto_install, ask_user=ask_user, parent=parent, target_dir=self.extlibs_dir)

    def show_dialog(self, parent=None) -> bool:
        """Show QMessageBox with progress — for QGIS."""
        try:
            from ._qt import QMessageBox, QProgressDialog, get_window_modality

            if self.is_installed():
                QMessageBox.information(parent, "qgis-sdk", "qgis-sdk is already installed.")
                return True

            choice = ask_user_to_install(parent)
            if choice == "cancel":
                return False
            if choice == "manual":
                show_manual_instructions(parent)
                return False

            # Show progress dialog while installing
            progress = QProgressDialog("Installing qgis-sdk...", "Cancel", 0, 0, parent)
            modality = get_window_modality()
            if modality is not None:
                progress.setWindowModality(modality)
            progress.setMinimumDuration(0)
            progress.show()

            try:
                success = self.install(target=self.extlibs_dir)
            finally:
                progress.close()

            if success:
                QMessageBox.information(parent, "qgis-sdk", "qgis-sdk installed successfully! Please restart QGIS or reload plugin.")
                return True
            else:
                QMessageBox.warning(parent, "qgis-sdk", "Failed to install qgis-sdk. Please install manually: pip install qgis-sdk")
                show_manual_instructions(parent)
                return False

        except Exception as e:
            print(f"[Installer] show_dialog failed: {e}")
            return self.ensure(auto_install=True, ask_user=ask_user, parent=parent)


def ensure_qgis_sdk(auto_install=True, ask_user=True, parent=None, plugin_dir=None) -> bool:
    """Convenience function."""
    installer = Installer(plugin_dir=plugin_dir)
    return installer.ensure(auto_install=auto_install, ask_user=ask_user, parent=parent)


__all__ = ["Installer", "ensure_qgis_sdk"]
