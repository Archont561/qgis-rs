"""TASK-57: qgis-sdk is a pure-Python console script with no Rust and no QGIS import.

Pinned at the public seam (`qgis_sdk.cli.main` and the installed console script):

* AC1 — no Rust subcommand, flag or build step, and no PyO3 or maturin in the
  distribution's build configuration.
* AC2 — the CLI runs without PyQGIS. The subprocess test blocks every QGIS
  module before importing the CLI, so a stray import fails the test instead of
  passing on a machine that happens to have QGIS installed. The package zip
  holds the plugin only, never the qgis_sdk package.
* AC3 — questionary asks only for what is missing at a terminal, and every
  question has a flag that answers it for CI.
* AC4 — `package` writes the plugin zip. The rest of the suite runs without
  QGIS; the bare-venv run is recorded in the task notes, not here.
"""

from __future__ import annotations

import subprocess
import sys
import types
import zipfile
from pathlib import Path

import pytest
import typer

from qgis_sdk import cli

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


# AC1 ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["rust", "init"],
        ["rust", "build"],
        ["build", "--rust"],
        ["package", "--rust"],
        ["test", "--rust"],
        ["dev", "--rust"],
        ["new", "rusty", "--rust"],
    ],
)
def test_rust_commands_and_flags_are_gone(argv, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # a `new` that wrongly accepted --rust must not write into the repo
    assert cli.main(argv) == 2
    assert not list(tmp_path.iterdir())


def test_no_rust_group_is_registered_on_the_app():
    command = typer.main.get_command(cli.app)
    assert "rust" not in command.commands


def test_build_configuration_has_no_rust_toolchain():
    text = PYPROJECT.read_text(encoding="utf-8")
    build_system = text.split("[build-system]", 1)[1].split("[project]", 1)[0]
    assert "setuptools" in build_system
    assert "maturin" not in text
    assert "pyo3" not in text.lower()


# AC2 ---------------------------------------------------------------------------

_NO_QGIS_CHILD = """
import os
import sys

for name in ("qgis", "qgis.core", "qgis.gui", "qgis.PyQt", "qgis_py", "qgis_sdk._core"):
    sys.modules[name] = None

from qgis_sdk import cli

out = sys.argv[1]
assert cli.main(["new", "no_qgis_plugin", "-o", out, "--no-ui"]) == 0
os.chdir(os.path.join(out, "no_qgis_plugin"))
assert cli.main(["package", "-o", os.path.join(out, "dist")]) == 0
print("ok")
"""


def test_cli_runs_with_every_qgis_module_blocked(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", _NO_QGIS_CHILD, str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_package_zip_holds_the_plugin_and_no_qgis_sdk_code(tmp_path, monkeypatch):
    assert cli.main(["new", "zip_plugin", "-o", str(tmp_path), "--no-ui"]) == 0
    monkeypatch.chdir(tmp_path / "zip_plugin")
    assert cli.main(["package", "-o", str(tmp_path / "dist")]) == 0

    names = zipfile.ZipFile(tmp_path / "dist" / "zip_plugin.zip").namelist()
    assert names
    assert all(name.startswith("zip_plugin/") for name in names)
    assert not [name for name in names if name.startswith("zip_plugin/qgis_sdk")]
    assert "zip_plugin/bootstrap.py" not in names


# AC3 ---------------------------------------------------------------------------


class _Answer:
    def __init__(self, value):
        self.value = value

    def ask(self):
        return self.value


def _fake_questionary(answers, asked):
    """A questionary stand-in: each question is recorded, then answered from `answers`."""
    module = types.ModuleType("questionary")

    def question(kind):
        def build(message, *args, **kwargs):
            asked.append((kind, message))
            return _Answer(answers[message])

        return build

    module.text = question("text")
    module.select = question("select")
    module.confirm = question("confirm")
    return module


@pytest.fixture
def terminal(monkeypatch):
    """Pretend the CLI runs at a terminal, so prompts are allowed."""
    monkeypatch.setattr(cli, "_interactive", lambda: True)


def test_missing_inputs_are_asked_at_a_terminal(tmp_path, monkeypatch, terminal):
    asked = []
    answers = {
        "Plugin name": "asked_plugin",
        "Plugin type": "processing",
        "Include UI dialogs?": False,
        "Author": "A. Author",
        "Author email": "author@example.org",
    }
    monkeypatch.setitem(sys.modules, "questionary", _fake_questionary(answers, asked))

    assert cli.main(["new", "-o", str(tmp_path)]) == 0
    assert [message for _, message in asked] == list(answers)
    assert (tmp_path / "asked_plugin" / "metadata.txt").is_file()


def test_flags_answer_every_question_and_nothing_is_asked(tmp_path, monkeypatch, terminal):
    asked = []
    monkeypatch.setitem(sys.modules, "questionary", _fake_questionary({}, asked))

    code = cli.main(
        [
            "new",
            "flagged",
            "-o",
            str(tmp_path),
            "--type",
            "general",
            "--no-ui",
            "--author",
            "A",
            "--email",
            "a@example.org",
        ]
    )

    assert code == 0
    assert asked == []
    assert (tmp_path / "flagged" / "metadata.txt").is_file()


def test_without_a_terminal_a_missing_name_fails_and_nothing_is_asked(tmp_path, monkeypatch, capsys):
    asked = []
    monkeypatch.setattr(cli, "_interactive", lambda: False)
    monkeypatch.setitem(sys.modules, "questionary", _fake_questionary({}, asked))

    code = cli.main(["new", "-o", str(tmp_path)])

    assert code == 2
    assert asked == []
    assert "plugin name is required" in capsys.readouterr().err


def test_without_a_terminal_defaults_apply_without_prompting(tmp_path, monkeypatch):
    asked = []
    monkeypatch.setattr(cli, "_interactive", lambda: False)
    monkeypatch.setitem(sys.modules, "questionary", _fake_questionary({}, asked))

    assert cli.main(["new", "defaults_plugin", "-o", str(tmp_path)]) == 0
    assert asked == []


@pytest.mark.parametrize(
    "option",
    ["--type", "--ui", "--author", "--email"],
)
def test_each_prompted_choice_has_a_flag(option):
    command = typer.main.get_command(cli.app).commands["new"]
    flags = {opt for param in command.params for opt in param.opts + param.secondary_opts}
    assert option in flags


def test_plugin_name_is_a_positional_argument_for_ci():
    command = typer.main.get_command(cli.app).commands["new"]
    arguments = [param.name for param in command.params if param.param_type_name == "argument"]
    assert arguments == ["name"]
