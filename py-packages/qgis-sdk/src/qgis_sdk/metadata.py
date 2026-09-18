"""``metadata.txt`` generation for QGIS plugins.

QGIS reads a plugin's metadata from a ``metadata.txt`` next to its
``__init__.py``. This module renders that file from the attributes declared on
a :class:`~qgis_sdk.plugin.Plugin` subclass, so the metadata can never drift
away from the code.

Now includes icon, changelog, plugin_dependencies and category validation.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .plugin import Plugin

__all__ = ["METADATA_FIELDS", "VALID_CATEGORIES", "render_metadata", "write_metadata", "validate_metadata"]

#: Valid QGIS plugin categories per https://plugins.qgis.org documentation
VALID_CATEGORIES = (
    "Vector",
    "Raster",
    "Database",
    "Mesh",
    "Web",
    "Processing",
    "Analysis",
    "Plugins",
)

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
    ("changelog", "changelog"),
    ("experimental", "experimental"),
    ("deprecated", "deprecated"),
    ("tags", "tags"),
    ("homepage", "homepage"),
    ("repository", "repository"),
    ("tracker", "tracker"),
    ("icon", "icon"),
    ("category", "category"),
    ("has_processing_provider", "hasProcessingProvider"),
    ("server", "server"),
    ("plugin_dependencies", "plugin_dependencies"),
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


def validate_metadata(plugin: type[Plugin]) -> list[str]:
    """Validate metadata and return list of errors."""
    errors = []
    
    # Required fields
    if not getattr(plugin, "name", None):
        errors.append("name is required")
    if not getattr(plugin, "version", None):
        errors.append("version is required")
    
    # Category validation
    category = getattr(plugin, "category", None)
    if category and category not in VALID_CATEGORIES:
        errors.append(f"category {category!r} must be one of {', '.join(VALID_CATEGORIES)}")
    
    # Version format
    version = getattr(plugin, "version", "")
    if version and not version[0].isdigit():
        # QGIS prefers version starting with digit
        pass  # not an error, just note
    
    # Icon validation — should be relative path if provided
    icon = getattr(plugin, "icon", None)
    if icon and os.path.isabs(icon):
        errors.append(f"icon {icon!r} should be relative path, not absolute")
    
    return errors


def render_metadata(plugin: type[Plugin]) -> str:
    """Render the full ``metadata.txt`` body for ``plugin``."""
    errors = validate_metadata(plugin)
    if errors:
        # We still render but could warn
        pass
    
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
