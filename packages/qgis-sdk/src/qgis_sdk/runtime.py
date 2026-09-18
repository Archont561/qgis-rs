"""Lazy access to PyQGIS.

Nothing in :mod:`qgis_sdk` imports ``qgis`` at module scope. That keeps the SDK
importable — and its logic unit-testable — on a machine without QGIS, which is
the whole point of the SDK's testing story.

Call :func:`qgis_core` (or :func:`qgis_gui`) from inside a function, at the
point where QGIS is genuinely required.
"""

from __future__ import annotations

import importlib
import os
from types import ModuleType

__all__ = [
    "PyQgisImportError",
    "expected_pythonpath",
    "qgis_core",
    "qgis_gui",
    "require_qgis",
]

#: Where the conda-forge ``qgis`` package installs its Python bindings. Its
#: activation script (``etc/conda/activate.d/qgis-activate.sh``) puts both of
#: these on ``PYTHONPATH``; pixi runs that script for ``pixi run`` and
#: ``pixi shell``.
BINDINGS_SUBPATHS = ("share/qgis/python", "share/qgis/python/plugins")


class PyQgisImportError(ImportError):
    """Raised when PyQGIS cannot be imported, with actionable diagnostics."""


def expected_pythonpath(prefix: str | None = None) -> list[str]:
    """Return the ``PYTHONPATH`` entries PyQGIS needs for ``prefix``.

    ``prefix`` defaults to ``$QGIS_PREFIX_PATH``, then ``$CONDA_PREFIX`` —
    the same fallbacks the conda-forge activation script uses.
    """
    prefix = prefix or os.environ.get("QGIS_PREFIX_PATH") or os.environ.get("CONDA_PREFIX")
    if not prefix:
        return []
    return [os.path.join(prefix, *sub.split("/")) for sub in BINDINGS_SUBPATHS]


def require_qgis() -> None:
    """Raise :class:`PyQgisImportError` unless ``qgis.core`` imports cleanly."""
    try:
        importlib.import_module("qgis.core")
    except ImportError as exc:  # pragma: no cover - exercised by the error text test
        expected = expected_pythonpath()
        hint = (
            "\n\nPyQGIS lives inside the QGIS environment. Run this code through "
            "pixi so the environment is activated:\n\n"
            "    pixi run -e sdk python your_script.py\n"
        )
        if expected:
            joined = os.pathsep.join(expected)
            hint += (
                "\nOr put the bindings on PYTHONPATH yourself:\n\n"
                f"    export PYTHONPATH={joined}:$PYTHONPATH\n"
                "\n(qgis.core also needs QGIS_PREFIX_PATH set to the same prefix.)"
            )
        else:
            hint += (
                "\nQGIS_PREFIX_PATH / CONDA_PREFIX are not set, so this does not "
                "look like an activated QGIS environment at all."
            )
        raise PyQgisImportError(f"cannot import qgis.core: {exc}{hint}") from exc


def qgis_core() -> ModuleType:
    """Return the ``qgis.core`` module, importing it on first use."""
    require_qgis()
    return importlib.import_module("qgis.core")


def qgis_gui() -> ModuleType:
    """Return the ``qgis.gui`` module, importing it on first use."""
    require_qgis()
    try:
        return importlib.import_module("qgis.gui")
    except ImportError as exc:
        raise PyQgisImportError(f"cannot import qgis.gui: {exc}") from exc
