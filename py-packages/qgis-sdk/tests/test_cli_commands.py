"""Every qgis-sdk command either does its work or fails with a non-zero exit.

Pinned at the `cli.main` seam. The retired Rust versions of `build`, `test`,
`install`, `dev`, `package` and `publish` printed a message and returned 0 without
doing anything. The commands here must write the artifact they name, or exit
non-zero when the work is not possible (for example, `dev` and an upload to the
QGIS plugin repository, which this package does not implement).
"""

from __future__ import annotations

import zipfile

import pytest

from qgis_sdk import cli


@pytest.fixture
def plugin_root(tmp_path, monkeypatch):
    """A scaffolded plugin, with the working directory set to its root."""
    assert cli.main(["new", "demo_plugin", "-o", str(tmp_path), "--no-ui"]) == 0
    root = tmp_path / "demo_plugin"
    monkeypatch.chdir(root)
    return root


def test_package_writes_a_zip_with_the_plugin_folder_and_its_metadata(plugin_root, tmp_path, capsys):
    out = tmp_path / "dist"

    code = cli.main(["package", "-o", str(out)])

    assert code == 0, capsys.readouterr().err
    archive = out / "demo_plugin.zip"
    assert archive.is_file()
    names = set(zipfile.ZipFile(archive).namelist())
    assert "demo_plugin/__init__.py" in names
    assert "demo_plugin/metadata.txt" in names
    assert not [name for name in names if "__pycache__" in name or name.endswith(".pyc")]


def test_package_without_a_plugin_package_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    code = cli.main(["package", "-o", str(tmp_path / "dist")])

    assert code != 0
    assert "plugin package" in capsys.readouterr().err


def test_build_writes_the_same_archive_as_package(plugin_root, capsys):
    code = cli.main(["build"])

    assert code == 0, capsys.readouterr().err
    assert (plugin_root / "dist" / "demo_plugin.zip").is_file()


def test_install_copies_the_plugin_into_the_profile(plugin_root, tmp_path, capsys):
    profile = tmp_path / "profile" / "plugins"

    code = cli.main(["install", "--profile", str(profile)])

    assert code == 0, capsys.readouterr().err
    assert (profile / "demo_plugin" / "__init__.py").is_file()
    assert (profile / "demo_plugin" / "metadata.txt").is_file()


def test_dev_is_not_implemented_and_says_so(plugin_root, capsys):
    code = cli.main(["dev"])

    assert code != 0
    assert "not implemented" in capsys.readouterr().err


def test_publish_without_dry_run_is_not_implemented(plugin_root, tmp_path, capsys):
    archive = tmp_path / "demo.zip"
    archive.write_bytes(b"PK")

    code = cli.main(["publish", "--zip", str(archive)])

    assert code != 0
    assert "not implemented" in capsys.readouterr().err


def test_publish_dry_run_names_the_archive_it_would_upload(tmp_path, capsys):
    archive = tmp_path / "demo.zip"
    archive.write_bytes(b"PK")

    code = cli.main(["publish", "--zip", str(archive), "--dry-run"])

    assert code == 0
    assert str(archive) in capsys.readouterr().out


def test_publish_dry_run_fails_when_the_archive_is_missing(tmp_path, capsys):
    code = cli.main(["publish", "--zip", str(tmp_path / "missing.zip"), "--dry-run"])

    assert code == 1
    assert "not found" in capsys.readouterr().err


def test_test_runs_the_python_suite_and_reports_its_result(plugin_root, monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)

        class Done:
            returncode = 3

        return Done()

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    code = cli.main(["test"])

    assert code == 3
    assert any(argv[1:3] == ["-m", "pytest"] for argv in calls)
