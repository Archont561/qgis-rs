"""Qt helpers — deprecated, use qgis_sdk._qt instead.

This module is kept for backward compatibility and now re-exports from _qt.
Will be removed in 0.3.0.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "qgis_sdk.qt is deprecated, use qgis_sdk._qt instead. "
    "This shim will be removed in 0.3.0.",
    DeprecationWarning,
    stacklevel=2,
)

from ._qt import make_action, make_dialog, make_web_view  # noqa: F401

__all__ = ["make_action", "make_dialog", "make_web_view"]
