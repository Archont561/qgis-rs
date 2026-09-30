#!/usr/bin/env bash
# pytest for one Python distribution.
#
# Usage: scripts/py-test.sh py-packages/qgis-rs [pytest args...]
#
# The extension module is NOT built here: turbo's `test` task depends on
# `build`, and `build` (scripts/py-build.sh) is what installs the wheel. Running
# maturin again from the test task is what used to make every test run a
# rebuild.
#
# QGIS_REQUIRE_NATIVE=1 turns the pure-Python fallbacks into hard failures, so a
# broken native extension cannot pass as a green suite.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"

pkg_dir="${1:?usage: scripts/py-test.sh <py-packages/NAME> [pytest args...]}"
shift || true

exec pixi run -e default bash -c '
  set -eu
  cd "$1"; shift
  QGIS_REQUIRE_NATIVE=1 python -m pytest tests -v "$@"
' _ "$pkg_dir" "$@"
