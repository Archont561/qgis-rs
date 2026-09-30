#!/usr/bin/env bash
# Build AND install one Python distribution — the whole maturin story for a
# package, in one task.
#
# Usage: scripts/py-build.sh py-packages/qgis-rs
#
# WHY IT ALSO INSTALLS. `maturin build` produces a wheel nobody can import, and
# `maturin develop` produces an import nobody can ship — so every consumer used
# to run both, and CI grew a separate "Build and install" step per package on
# top of the turbo `build` task that had already compiled the same crate. Here
# the release wheel is built once and then *that exact artifact* is installed
# into the environment. One compile, and the thing under test is the thing that
# gets published.
#
# WHY NOT `maturin develop`. `develop` requires an activated virtualenv and
# shells out to pip anyway; the pixi `default` environment already is the
# target interpreter (it is the one QGIS was compiled against), so a venv layered
# on top of it would only hide QGIS's own site-packages. `pip install` into the
# prefix has no such requirement — which is why there is no venv step anywhere
# in this repo.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"

pkg_dir="${1:?usage: scripts/py-build.sh <py-packages/NAME> [maturin args...]}"
shift || true
[ -f "$pkg_dir/pyproject.toml" ] || { echo "no pyproject.toml in $pkg_dir" >&2; exit 1; }

exec pixi run -e default bash -c '
  set -eu
  cd "$1"; shift
  # A stale wheel from an earlier version would make the glob below ambiguous.
  rm -rf dist
  maturin build --release --out dist "$@"
  # --no-deps: every runtime dependency is a conda package owned by pixi, and
  # letting pip resolve them would shadow the QGIS-matched builds with PyPI ones.
  python -m pip install --force-reinstall --no-deps --no-index dist/*.whl
' _ "$pkg_dir" "$@"
