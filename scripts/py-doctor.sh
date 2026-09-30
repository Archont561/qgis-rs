#!/usr/bin/env bash
# qgis-sdk's environment self-check. Assumes `build` already installed the
# extension (turbo orders it), so it only runs the script.
set -euo pipefail
# shellcheck source=scripts/_common.sh
source "$(dirname "$0")/_common.sh"
exec pixi run -e default bash -c '
  set -eu
  cd py-packages/qgis-sdk
  QGIS_REQUIRE_NATIVE=1 python scripts/doctor.py "$@"
' _ "$@"
