"""`qgis-sdk new` always uses the Python scaffold.

Pinned at the public CLI seam (`qgis_sdk.cli.main`). The retired Rust scaffold
produced an older, smaller plugin (no network, tasks or services package) and
was selected whenever the native extension was importable. It is removed, so
even with a native core present, `new` must write the Python scaffold tree.
"""

from __future__ import annotations



from qgis_sdk import cli
from qgis_sdk.scaffold import scaffold_plugin


def _tree(root):
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_new_scaffolds_a_plugin_tree(tmp_path, capsys):
    code = cli.main(["new", "demo_plugin", "-o", str(tmp_path)])

    assert code == 0, capsys.readouterr().err
    assert (tmp_path / "demo_plugin" / "metadata.txt").is_file()


def test_new_writes_the_python_scaffold_tree(tmp_path):
    cli_dir = tmp_path / "cli"
    direct_dir = tmp_path / "direct"
    cli_dir.mkdir()
    direct_dir.mkdir()

    assert cli.main(["new", "demo_plugin", "-o", str(cli_dir), "--no-ui"]) == 0
    scaffold_plugin("demo_plugin", str(direct_dir), "general", False, with_ui=False)

    assert _tree(cli_dir) == _tree(direct_dir)
