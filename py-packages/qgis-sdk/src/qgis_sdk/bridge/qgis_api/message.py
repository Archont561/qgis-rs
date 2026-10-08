"""qgis_sdk.bridge.qgis_api.message — messageBar API."""

from __future__ import annotations

from ._resolver import resolve_qgis_resource


class MessageAPI:
    def __init__(self, iface=None):
        self.iface = iface

    def _push(self, title: str, message: str, level: int = 0, duration: int = 5) -> bool:
        iface = resolve_qgis_resource("iface", self.iface)
        if not iface:
            print(f"[Message] {title}: {message}")
            return True
        try:
            # level: 0 Info, 1 Warning, 2 Critical, 3 Success
            from qgis.core import Qgis
            level_map = {
                0: Qgis.Info,
                1: Qgis.Warning,
                2: Qgis.Critical,
                3: Qgis.Success,
            }
            qgis_level = level_map.get(level, Qgis.Info)
            iface.messageBar().pushMessage(title, message, level=qgis_level, duration=duration)
            return True
        except Exception as e:
            print(f"[MessageAPI] push failed: {e}")
            # Fallback
            try:
                iface.messageBar().pushMessage(title, message, duration=duration)
                return True
            except Exception:
                print(f"[Message] {title}: {message}")
                return True

    def info(self, title: str, message: str, duration: int = 5) -> bool:
        return self._push(title, message, level=0, duration=duration)

    def warning(self, title: str, message: str, duration: int = 5) -> bool:
        return self._push(title, message, level=1, duration=duration)

    def critical(self, title: str, message: str, duration: int = 5) -> bool:
        return self._push(title, message, level=2, duration=duration)

    def success(self, title: str, message: str, duration: int = 5) -> bool:
        return self._push(title, message, level=3, duration=duration)

    def push(self, title: str, text: str, level: int = 0, duration: int = 5) -> bool:
        return self._push(title, text, level=level, duration=duration)
