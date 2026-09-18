"""``metadata.txt`` generation for QGIS plugins.

QGIS reads a plugin's metadata from a ``metadata.txt`` next to its
``__init__.py``. This module renders that file from the attributes declared on
a :class:`~qgis_sdk.plugin.Plugin` subclass, so the metadata can never drift
away from the code.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .plugin import Plugin

__all__ = ["METADATA_FIELDS", "render_metadata", "write_metadata"]

#: Plugin attribute -> metadata.txt key, in the order QGIS expects them.
METADATA_FIELDS: tuple[tuple[str, str], ...] = (
    ("name", "name"),
    ("qgis_min_version", "qgisMinimumVersion"),
    ("qgis_max_version", "qgisMaximumVersion"),
    ("description", "description"),
    ("about", "about"),
    ("version", "version"),
    ("author", "author"),
    ("email", "email"),
    ("category", "category"),
    ("tags", "tags"),
    ("homepage", "homepage"),
    ("repository", "repository"),
    ("tracker", "tracker"),
    ("experimental", "experimental"),
    ("deprecated", "deprecated"),
    ("has_processing_provider", "hasProcessingProvider"),
    ("server", "server"),
)


def _normalise(value: object) -> str | None:
    """Flatten a declared attribute into a single metadata.txt line."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Iterable):
        text = ", ".join(str(item).strip() for item in value if str(item).strip())
        return text or None
    return str(value)


def metadata_items(plugin: type[Plugin]) -> list[tuple[str, str]]:
    """Return the ``(key, value)`` pairs for ``plugin``, skipping unset ones."""
    items: list[tuple[str, str]] = []
    for attribute, key in METADATA_FIELDS:
        value = _normalise(getattr(plugin, attribute, None))
        if value is not None:
            items.append((key, value))
    return items


def render_metadata(plugin: type[Plugin]) -> str:
    """Render the full ``metadata.txt`` body for ``plugin``."""
    lines = ["[general]"]
    lines += [f"{key}={value}" for key, value in metadata_items(plugin)]
    return "\n".join(lines) + "\n"


def write_metadata(plugin: type[Plugin], directory: str | os.PathLike[str]) -> str:
    """Write ``metadata.txt`` into ``directory`` and return its path."""
    path = os.path.join(os.fspath(directory), "metadata.txt")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_metadata(plugin))
    return path


def as_mapping(plugin: type[Plugin]) -> Mapping[str, str]:
    """Return the metadata as a mapping, for tests and tooling."""
    return dict(metadata_items(plugin))
