#!/usr/bin/env bash
# Writes formatting for the Rust and C++ trees. `--cpp` limits it to clang-format.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"

cpp_only=0
[ "${1-}" = --cpp ] && cpp_only=1

format_cpp() {
  pixi run -e default bash -c '
    find crates/qgis-sys/src crates/qgis-sys/include \
      \( -name "*.cpp" -o -name "*.h" \) -print0 |
      xargs -0 --no-run-if-empty clang-format -i
  '
}

if [ "$cpp_only" = 1 ]; then
  format_cpp
  exit 0
fi

bun x biome format --write crates/package.json
pixi run -e default cargo fmt --all
format_cpp
