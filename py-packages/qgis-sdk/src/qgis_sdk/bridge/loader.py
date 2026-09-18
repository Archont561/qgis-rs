"""qgis_sdk.bridge.loader — load bridge description from JSON or class."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Type, Union

from .description import BridgeDescription


def load_bridge_description(
    source: Union[str, Path, Dict[str, Any], Type, BridgeDescription],
) -> BridgeDescription:
    """Load BridgeDescription from various sources.

    Args:
        source: can be:
            - Path to JSON file
            - JSON string
            - dict
            - Python class
            - BridgeDescription instance

    Returns:
        BridgeDescription
    """
    if isinstance(source, BridgeDescription):
        return source

    if isinstance(source, type):
        # Class
        return BridgeDescription.from_class(source)

    if isinstance(source, dict):
        return BridgeDescription.from_dict(source)

    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.exists():
            # File
            text = path.read_text(encoding="utf-8")
            try:
                return BridgeDescription.from_json(text)
            except Exception:
                # Maybe it's a dotted path to class?
                pass
        # Try as JSON string
        if isinstance(source, str):
            stripped = source.strip()
            if stripped.startswith("{"):
                try:
                    return BridgeDescription.from_json(stripped)
                except Exception:
                    pass
            # Try as dotted path: "my_module:MyBridge" or "my_module.MyBridge"
            if "." in source or ":" in source:
                try:
                    from .codegen import load_bridge_class
                    cls = load_bridge_class(source)
                    return BridgeDescription.from_class(cls)
                except Exception:
                    pass

    raise ValueError(f"Cannot load bridge description from {source!r}")


def load_bridge_description_from_window(window: Any = None) -> Optional[BridgeDescription]:
    """Try to load description from window.__QGIS_BRIDGE_DESCRIPTION__ (for JS side, but also Python testing)."""
    # In Python, window may be a dict or object with attribute
    try:
        if window is None:
            # Try to get from global? Not available in Python
            return None
        # If window is dict with description
        if isinstance(window, dict) and "__QGIS_BRIDGE_DESCRIPTION__" in window:
            data = window["__QGIS_BRIDGE_DESCRIPTION__"]
            if isinstance(data, str):
                return BridgeDescription.from_json(data)
            elif isinstance(data, dict):
                return BridgeDescription.from_dict(data)
        # If window has attribute
        if hasattr(window, "__QGIS_BRIDGE_DESCRIPTION__"):
            data = getattr(window, "__QGIS_BRIDGE_DESCRIPTION__")
            if isinstance(data, str):
                return BridgeDescription.from_json(data)
            elif isinstance(data, dict):
                return BridgeDescription.from_dict(data)
    except Exception as e:
        print(f"[loader] failed to load from window: {e}")
    return None
