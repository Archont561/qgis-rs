"""Which execution layer this process can actually reach.

Four layers, and a test must be able to tell them apart before it runs:

* **pure** — no Qt, no QGIS, no WebEngine. The default, and the only one CI's
  bare virtualenv has;
* **Qt** — ``PyQt5.QtWidgets`` imports, so widgets can be built under
  ``QT_QPA_PLATFORM=offscreen``;
* **QGIS** — ``qgis.core`` imports, and possibly a live ``QgsApplication``;
* **WebEngine** — ``PyQt5.QtWebEngineWidgets`` is installed.

The detector never *creates* an application object, and never imports
``QtWebEngineWidgets`` — importing that module after a ``QCoreApplication``
exists is an error in Qt, so its availability is answered with
``importlib.util.find_spec`` instead. Detection must be free of side effects,
because every ``require_*`` below is called from a test that has not yet
decided whether it is allowed to run.
"""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class QgisTestEnvironment:
    """Detected runtime capabilities for a pytest session.

    The detector only imports ``qgis.core`` and inspects the application
    singleton; it does not create a QApplication or QgsApplication. That makes
    it safe to use in both a bare Python virtualenv and a QGIS host process.
    """

    qgis_available: bool
    qt_available: bool
    qgis_application_available: bool
    webengine_available: bool = False
    qgis_version: Optional[str] = None
    qgis_import_error: Optional[str] = None

    @property
    def pure_python(self) -> bool:
        """Whether the PyQGIS bindings are unavailable."""
        return not self.qgis_available

    @property
    def is_pure_python(self) -> bool:
        return self.pure_python

    @property
    def is_qgis(self) -> bool:
        return self.qgis_available

    @property
    def backend(self) -> str:
        """A stable label suitable for test output and CI diagnostics."""
        return "qgis" if self.qgis_available else "pure-python"

    @property
    def layers(self) -> frozenset:
        """The execution layers this process can reach, by name.

        ``"pure"`` is always present — a pure test needs nothing — and the rest
        appear only when their binding really imports.
        """
        reachable = {"pure"}
        if self.qt_available:
            reachable.add("qt")
        if self.qgis_available:
            reachable.add("qgis")
        if self.webengine_available:
            reachable.add("webengine")
        return frozenset(reachable)

    def supports(self, layer: str) -> bool:
        """Whether one named execution layer is reachable here."""
        return layer in self.layers

    # ── prerequisites ───────────────────────────────────────────────────────
    #
    # A missing layer is a skip, never a fallback to a fake: a suite that
    # answers a QGIS question with a fake has reported a green it did not earn.

    def require_qgis(self) -> None:
        """Skip the current test when PyQGIS is not importable."""
        if not self.qgis_available:
            import pytest

            pytest.skip("requires an importable qgis.core runtime")

    def require_qt(self) -> None:
        """Skip the current test when PyQt5 is not importable."""
        if not self.qt_available:
            import pytest

            pytest.skip("requires an importable PyQt5 runtime")

    def require_webengine(self) -> None:
        """Skip the current test when QtWebEngine is not installed."""
        if not self.webengine_available:
            import pytest

            pytest.skip("requires PyQt5.QtWebEngineWidgets")


def detect_qgis_environment() -> QgisTestEnvironment:
    """Inspect whether tests run with PyQGIS, Qt, WebEngine or pure Python.

    This function is deliberately independent of pytest so applications and
    custom test plugins can use the same check. ``qgis_available`` means that
    ``qgis.core`` imports; ``qgis_application_available`` additionally means a
    live ``QgsApplication`` singleton already exists; ``webengine_available``
    means the module is installed, answered without importing it.
    """
    qgis_available = False
    qgis_application_available = False
    qgis_version = None
    qgis_import_error = None

    try:
        core = importlib.import_module("qgis.core")
    except (ImportError, ModuleNotFoundError) as exc:
        qgis_import_error = str(exc)
    except Exception as exc:  # pragma: no cover - depends on a broken QGIS install
        qgis_import_error = f"{type(exc).__name__}: {exc}"
    else:
        qgis_available = True
        qgis_version = _qgis_version(core)
        application = getattr(core, "QgsApplication", None)
        if application is not None and hasattr(application, "instance"):
            try:
                qgis_application_available = application.instance() is not None
            except Exception:  # pragma: no cover - depends on QGIS bindings
                qgis_application_available = False

    try:
        importlib.import_module("PyQt5.QtWidgets")
    except (ImportError, ModuleNotFoundError):
        qt_available = False
    except Exception:  # pragma: no cover - depends on the Qt installation
        qt_available = False
    else:
        qt_available = True

    return QgisTestEnvironment(
        qgis_available=qgis_available,
        qt_available=qt_available,
        qgis_application_available=qgis_application_available,
        webengine_available=_webengine_installed(),
        qgis_version=qgis_version,
        qgis_import_error=qgis_import_error,
    )


def _qgis_version(core) -> Optional[str]:
    """The release QGIS reports, e.g. ``3.44.14-Solothurn``, or ``None``.

    ``qgis.core`` does not export a ``QGIS_VERSION`` constant in the bindings
    this suite runs against; the release is ``Qgis.version()``. Reading the
    constant instead answered ``None`` for every runtime, which is how the
    version went missing from test output without anything failing.
    """
    qgis = getattr(core, "Qgis", None)
    if qgis is not None and hasattr(qgis, "version"):
        try:
            return str(qgis.version())
        except Exception:  # pragma: no cover - depends on the QGIS bindings
            pass
    legacy = getattr(core, "QGIS_VERSION", None)
    return None if legacy is None else str(legacy)


def _webengine_installed() -> bool:
    """Whether ``PyQt5.QtWebEngineWidgets`` is installed, without importing it.

    Qt requires that module to be imported *before* any ``QCoreApplication``
    exists; a detector that imported it would be a landmine in a session that
    already built a ``QApplication``. ``find_spec`` answers the only question
    a test needs — is it installed — with no import at all.
    """
    try:
        return importlib.util.find_spec("PyQt5.QtWebEngineWidgets") is not None
    except (ImportError, ValueError):  # pragma: no cover - depends on the installation
        return False


__all__ = ["QgisTestEnvironment", "detect_qgis_environment"]
