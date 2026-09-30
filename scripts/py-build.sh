#!/usr/bin/env bash
# Build AND install one Python distribution — the whole maturin story for a
# package, in one task.
#
# Usage: scripts/py-build.sh py-packages/qgis-rs
#
# WHY IT DOES BOTH. `maturin build` produces a wheel nobody can import, and
# `maturin develop` produces an import nobody can ship, so every consumer used
# to run both by hand — turbo's `build` task, then a separate "Build and
# install" step per package in CI, recompiling what turbo had already built.
# Here one task does both, cargo compiles once, and `test` / `coverage` only
# have to run pytest.
#
#   1. maturin develop --release
#      Installs into the environment AND — this is the part a plain
#      `pip install` of the wheel cannot do — drops the compiled
#      `qgis_rs._core` / `qgis_sdk._core` extension next to the pure-Python
#      sources in this mixed-layout project. Both distributions set
#      `python-source` and list `python` (resp. `src`) in pytest's `testpaths`,
#      so pytest puts the SOURCE tree on sys.path and imports the package from
#      there. Without the extension sitting in that tree, the package silently
#      falls back to its pure-Python implementation and
#      `test_native_extension_is_used_in_ci` fails — which is exactly what it
#      is there to catch.
#
#   2. maturin build --release --out dist
#      The shippable wheel. Same profile and features as step 1, so cargo
#      reuses the compilation and this is a re-link and a zip.
#
# WHY THERE IS NO VIRTUALENV STEP. `maturin develop` wants an activated
# environment, and the pixi `default` environment already is one: it exports
# CONDA_PREFIX, and maturin treats a conda prefix as the install target. It is
# also the interpreter QGIS was compiled against, so a venv layered on top
# would only hide QGIS's own site-packages. This is why CI no longer runs
# `python -m venv` or `pip install maturin pytest pytest-cov`.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"

pkg_dir="${1:?usage: scripts/py-build.sh <py-packages/NAME> [maturin args...]}"
shift || true
[ -f "$pkg_dir/pyproject.toml" ] || { echo "no pyproject.toml in $pkg_dir" >&2; exit 1; }

exec pixi run -e default bash -c '
  set -eu
  cd "$1"; shift
  # A stale wheel from an earlier version would make dist/*.whl ambiguous for
  # anything that globs it.
  rm -rf dist
  maturin develop --release "$@"
  maturin build --release --out dist "$@"
' _ "$pkg_dir" "$@"
