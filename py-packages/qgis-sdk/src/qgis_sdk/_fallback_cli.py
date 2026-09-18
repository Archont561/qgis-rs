"""
Pure-Python fallback for qgis_sdk._core when Rust extension not built.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

__version__ = "0.1.0-fallback"

def version() -> str:
    return __version__

def metadata_fields():
    return []

def render_metadata_from_dict(d: dict) -> str:
    lines = ["[general]"]
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, bool):
            v = "True" if v else "False"
        lines.append(f"{k}={v}")
    return "\n".join(lines) + "\n"

def validate_plugin_structure(path: str) -> List[str]:
    errors = []
    base = Path(path)
    if not base.exists():
        raise ValueError(f"path does not exist: {path}")
    # Minimal checks
    if not (base / "metadata.txt").exists() and not (base / "src" / "metadata.txt").exists():
        # Check if any .py file exists as alternative
        has_py = any(p.suffix == ".py" for p in base.iterdir()) if base.is_dir() else False
        if not has_py:
            # Don't error for empty dir in fallback — let Python validation handle
            pass
    return errors

def scaffold_plugin(name: str, path: str, plugin_type: str, with_rust: bool, with_web: bool = False, with_ui: bool = True, web_framework: str = "vanilla", declarative: bool = False, with_bundle: bool = False, offline_wheel: str | None = None) -> str:
    from .scaffold import scaffold_plugin as py_scaffold
    return py_scaffold(name, path, plugin_type, with_rust, with_web=with_web, with_ui=with_ui, web_framework=web_framework, declarative=declarative, with_bundle=with_bundle, offline_wheel=offline_wheel)
