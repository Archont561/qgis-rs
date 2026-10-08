"""The subprocess runner behind the QGIS integration test, proven without QGIS.

These run in the pure gate: they spawn plain Python children, so they check the
isolation contract (environment, exit status, timeout, diagnostics, digests)
on any machine. The QGIS-hosted test then only has to prove QGIS itself.
"""

from __future__ import annotations

import os
from pathlib import Path

from qgis_subprocess import QgisRun, run_in_subprocess, tree_digest


def test_the_child_gets_offscreen_qt_and_no_bytecode(tmp_path: Path) -> None:
    run = run_in_subprocess(
        "import os, sys; "
        "sys.stdout.write(os.environ['QT_QPA_PLATFORM'] + ' ' "
        "+ os.environ['PYTHONDONTWRITEBYTECODE'])",
        cwd=tmp_path,
    )

    assert run.succeeded
    assert run.stdout == "offscreen 1"


def test_pythonpath_entries_are_prepended_not_substituted(tmp_path: Path) -> None:
    extra = tmp_path / "extra"
    extra.mkdir()
    run = run_in_subprocess(
        "import os, sys; sys.stdout.write(os.environ['PYTHONPATH'])",
        cwd=tmp_path,
        pythonpath=[extra],
    )

    assert run.succeeded
    assert run.stdout.split(os.pathsep)[0] == str(extra)


def test_a_failing_child_reports_its_status_and_both_streams(tmp_path: Path) -> None:
    run = run_in_subprocess(
        "import sys; sys.stdout.write('out-marker'); "
        "sys.stderr.write('err-marker'); sys.exit(3)",
        cwd=tmp_path,
    )

    assert not run.succeeded
    assert run.returncode == 3
    report = run.diagnostics(qgis_version="3.44.14-Solothurn")
    assert "exit status 3" in report
    assert "out-marker" in report
    assert "err-marker" in report
    assert "3.44.14-Solothurn" in report


def test_a_hung_child_is_killed_and_its_partial_output_is_kept(tmp_path: Path) -> None:
    run = run_in_subprocess(
        "import sys, time; sys.stdout.write('before-hang'); sys.stdout.flush(); "
        "time.sleep(60)",
        cwd=tmp_path,
        timeout=2,
    )

    assert run.timed_out
    assert not run.succeeded
    assert "before-hang" in run.diagnostics()
    assert "timed out" in run.describe_exit()


def test_a_child_killed_by_a_signal_is_named_as_one(tmp_path: Path) -> None:
    run = QgisRun(returncode=-11, stdout="", stderr="")

    assert not run.succeeded
    assert run.describe_exit() == "killed by signal 11"


def test_the_digest_sees_an_edit_an_addition_and_a_removal(tmp_path: Path) -> None:
    (tmp_path / "plugin.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "rows.txt").write_text("one\n", encoding="utf-8")
    before = tree_digest(tmp_path)

    (tmp_path / "plugin.py").write_text("a = 2\n", encoding="utf-8")
    edited = tree_digest(tmp_path)
    (tmp_path / "extra.py").write_text("", encoding="utf-8")
    added = tree_digest(tmp_path)
    (tmp_path / "data" / "rows.txt").unlink()
    removed = tree_digest(tmp_path)

    assert edited != before
    assert set(added) - set(edited) == {"extra.py"}
    assert set(edited) - set(removed) == {"data/rows.txt"}
    assert tree_digest(tmp_path) == removed
