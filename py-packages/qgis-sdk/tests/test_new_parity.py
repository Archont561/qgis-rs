"""`qgis-sdk new` always uses the Python scaffold.

Pinned at the public CLI seam (`qgis_sdk.cli.main`). The retired Rust scaffold
produced an older, smaller plugin (no network, tasks or services package) and
was selected whenever the native extension was importable. It is removed, so
even with a native core present, `new` must write the Python scaffold tree.
"""

from __future__ import annotations

import pytest

from qgis_sdk import cli
from qgis_sdk.scaffold import scaffold_plugin


class _ForbiddenNativeCore:
    """Stands in for the retired native module. Any call is a failure."""

    def scaffold_plugin(self, *args, **kwargs):
        raise AssertionError("native scaffold must not be called")


@pytest.fixture
def native_core_present(monkeypatch):
    monkeypatch.setattr(cli, "HAS_RUST", True, raising=False)
    monkeypatch.setattr(cli, "core", _ForbiddenNativeCore(), raising=False)


def _tree(root):
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_new_does_not_call_the_native_scaffold(native_core_present, tmp_path, capsys):
    code = cli.main(["new", "demo_plugin", "-o", str(tmp_path)])

    assert code == 0, capsys.readouterr().err
    assert (tmp_path / "demo_plugin" / "metadata.txt").is_file()


def test_new_writes_the_python_scaffold_tree(native_core_present, tmp_path):
    cli_dir = tmp_path / "cli"
    direct_dir = tmp_path / "direct"
    cli_dir.mkdir()
    direct_dir.mkdir()

    assert cli.main(["new", "demo_plugin", "-o", str(cli_dir), "--no-ui"]) == 0
    scaffold_plugin("demo_plugin", str(direct_dir), "general", False, with_ui=False)

    assert _tree(cli_dir) == _tree(direct_dir)
