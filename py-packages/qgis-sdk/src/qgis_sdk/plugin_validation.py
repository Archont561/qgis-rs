"""Plugin structure checks behind `qgis-sdk validate`.

This is the union of the two Rust rule sets it replaces (the `qgis-sdk` crate
and `qgis-sdk-core`). It is the only implementation: there is no native
alternative to fall back from.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

QWEBCHANNEL_HINT = 'add <script src="qrc:///qtwebchannel/qwebchannel.js">'


def _roots(base: Path) -> List[Path]:
    """The plugin root, then the nested `<dirname>/` package directory."""
    return [base, base / base.name]


def _metadata_path(base: Path) -> Path | None:
    for candidate in (base / "metadata.txt", base / "src" / "metadata.txt"):
        if candidate.exists():
            return candidate
    return None


def _metadata_errors(path: Path) -> List[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"cannot read metadata.txt: {exc}"]
    errors = []
    if "[general]" not in content:
        errors.append("metadata.txt missing [general] section")
    if "name=" not in content:
        errors.append("metadata.txt missing name")
    if "version=" not in content:
        errors.append("metadata.txt missing version")
    return errors


def _has_root_python(base: Path) -> bool:
    return base.is_dir() and any(p.suffix == ".py" for p in base.iterdir())


def _web_errors(base: Path) -> List[str]:
    errors = []
    for root in _roots(base):
        web = root / "web"
        if not web.is_dir():
            continue
        for page in sorted(web.iterdir()):
            if page.suffix != ".html":
                continue
            try:
                content = page.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "qwebchannel" not in content and "QWebChannel" not in content:
                errors.append(f"{page} missing qwebchannel.js reference ({QWEBCHANNEL_HINT})")
    return errors


def validate_plugin_structure(path: str) -> Tuple[List[str], List[str]]:
    """Return `(errors, notes)` for the plugin at `path`.

    Raises `ValueError` when the path does not exist. `notes` describe the UI
    and Web surfaces found; they are informational and printed only when the
    structure is valid.
    """
    base = Path(path)
    if not base.exists():
        raise ValueError(f"path does not exist: {path}")

    errors: List[str] = []
    metadata = _metadata_path(base)
    if metadata is not None:
        errors.extend(_metadata_errors(metadata))
    elif not _has_root_python(base):
        errors.append("missing metadata.txt")

    errors.extend(_web_errors(base))

    notes: List[str] = []
    if any((root / "ui").exists() for root in _roots(base)):
        notes.append("UI: .ui files found")
    if any((root / "web").exists() for root in _roots(base)):
        notes.append("Web: HTML files found, QWebChannel bridge ready")
    return errors, notes
