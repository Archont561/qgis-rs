#!/usr/bin/env bash
# clang-format gate for the C++ shim. With arguments it checks exactly those
# files (lefthook passes the staged ones); with none it checks the whole tree.
# Assumes it already runs inside the `default` pixi environment.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"

if [ "$#" -gt 0 ]; then
  clang-format --dry-run --Werror "$@"
else
  find crates/qgis-sys/src crates/qgis-sys/include \
    \( -name '*.cpp' -o -name '*.h' \) -print0 |
    xargs -0 --no-run-if-empty clang-format --dry-run --Werror
fi
