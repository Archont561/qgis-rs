#!/usr/bin/env bash
# pytest + coverage for one Python distribution, writing the Cobertura XML that
# Codecov reads into the repo-wide target/coverage/ directory (the same place
# the Rust lcov lands, so CI uploads one directory).
#
# Usage: scripts/py-coverage.sh py-packages/qgis-rs qgis_rs
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"

pkg_dir="${1:?usage: scripts/py-coverage.sh <py-packages/NAME> <import_name>}"
module="${2:?usage: scripts/py-coverage.sh <py-packages/NAME> <import_name>}"
out="$REPO_ROOT/target/coverage/python-$(basename "$pkg_dir").xml"
mkdir -p "$REPO_ROOT/target/coverage"

exec pixi run -e default bash -c '
  set -eu
  cd "$1"
  QGIS_REQUIRE_NATIVE=1 python -m pytest tests -v \
    --cov="$2" \
    --cov-report=term-missing \
    --cov-report=xml:"$3"
' _ "$pkg_dir" "$module" "$out"
