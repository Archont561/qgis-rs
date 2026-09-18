#!/usr/bin/env python
"""Environment doctor for the qgis-sdk pixi environment.

Run it as ``pixi run -e sdk sdk-doctor``. It prints the interpreter in use, the
PyQGIS import paths, and whether ``qgis.core`` and ``qgis_sdk`` actually
resolve. Exits non-zero if anything is missing.
"""

from __future__ import annotations

import os
import sys

from qgis_sdk import __version__, expected_pythonpath


def main() -> int:
    print(f"python       {sys.executable}")
    print(f"version      {sys.version.split()[0]}")
    print(f"prefix       {os.environ.get('QGIS_PREFIX_PATH') or os.environ.get('CONDA_PREFIX') or '(unset)'}")
    print(f"QT_QPA       {os.environ.get('QT_QPA_PLATFORM', '(unset)')}")
    print(f"qgis_sdk     {__version__}")

    for path in expected_pythonpath():
        marker = "ok " if os.path.isdir(path) else "MISSING"
        print(f"bindings     [{marker}] {path}")

    failures = 0
    for module in ("qgis.core", "qgis.gui"):
        try:
            __import__(module)
        except ImportError as exc:
            failures += 1
            print(f"{module:<12} FAILED: {exc}")
        else:
            print(f"{module:<12} ok")

    try:
        from qgis.core import Qgis  # type: ignore[import-not-found]

        print(f"qgis version {Qgis.QGIS_VERSION}")
    except ImportError:
        failures += 1
        print("qgis version unavailable")

    print("result       " + ("FAIL" if failures else "PASS"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
