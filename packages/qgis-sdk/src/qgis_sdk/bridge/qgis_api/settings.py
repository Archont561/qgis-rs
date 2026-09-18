"""qgis_sdk.bridge.qgis_api.settings — settings API for JS."""

from __future__ import annotations


class SettingsAPI:
    def __init__(self, plugin_name: str = "my_plugin"):
        self.plugin_name = plugin_name

    def get(self, key: str, default: str = "") -> str:
        try:
            from qgis.core import QgsSettings
            return QgsSettings().value(f"{self.plugin_name}/{key}", default)
        except ImportError:
            # Fallback to simple dict or env
            return default
        except Exception:
            return default

    def set(self, key: str, value: str) -> bool:
        try:
            from qgis.core import QgsSettings
            QgsSettings().setValue(f"{self.plugin_name}/{key}", value)
            return True
        except ImportError:
            return True
        except Exception as e:
            print(f"[SettingsAPI] set failed: {e}")
            return False
