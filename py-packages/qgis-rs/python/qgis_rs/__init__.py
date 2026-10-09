"""Deprecated alias: the `qgis-rs` distribution is now `qgis-py`.

Every public name is forwarded to `qgis_py`, so `qgis_rs.Extent is qgis_py.Extent`.
This package keeps its own submodules (`qgis_rs.cli`), so the deprecation notice
on the `qgis-rs` console script still runs. Import `qgis_py` in new code.
"""

import warnings as _warnings

import qgis_py as _impl
from qgis_py import *  # noqa: F401,F403 - the alias re-exports the whole API

warnings_message = "the qgis-rs distribution is renamed qgis-py; import qgis_py instead of qgis_rs"
_warnings.warn(warnings_message, DeprecationWarning, stacklevel=2)

__all__ = list(_impl.__all__)


def __getattr__(name: str):
    # Names that are not in __all__ (for example `_core`, `_api`, `_transport`)
    # still resolve to the same objects in qgis_py.
    return getattr(_impl, name)
