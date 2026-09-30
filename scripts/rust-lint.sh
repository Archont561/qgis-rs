#!/usr/bin/env bash
# The Rust/C++ lint gate, in four passes that get progressively more expensive:
#
#   1. biome on the facade package.json
#   2. cargo fmt --check + clang-format --dry-run  (no compilation)
#   3. cargo clippy -D warnings                    (compiles Rust)
#   4. clang-tidy                                  (needs cxx's generated
#                                                   headers, so qgis-sys must
#                                                   have been built first)
#
# Pass 4 is the reason this is a script and not a manifest one-liner: the
# include path has to be *discovered* (the cxxbridge out-dir is hashed, Qt
# headers live under include/qt or include/qt6 depending on the build, and the
# GCC internal include dir carrying stddef.h is version-stamped).
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"

bun x biome check crates/package.json

pixi run -e default bash -c '
  set -eu
  cd crates
  cargo fmt --all --check
  find qgis-sys/src qgis-sys/include \( -name "*.cpp" -o -name "*.h" \) -print0 |
    xargs -0 --no-run-if-empty clang-format --dry-run --Werror
  cargo clippy --workspace --all-targets -- -D warnings
'

pixi run -e default bash -c '
  set -eu
  cd crates
  # clang-tidy parses the shim against the real headers, so the generated
  # cxxbridge output must exist before it runs.
  cargo build -p qgis-sys >/dev/null

  QT_INC="$CONDA_PREFIX/include/qt"
  [ -d "$QT_INC" ] || QT_INC="$CONDA_PREFIX/include/qt6"

  CXX_OUT="$(find ../target/debug/build/qgis-sys-*/out/cxxbridge -maxdepth 0 2>/dev/null | head -1)"
  [ -n "$CXX_OUT" ] || { echo "clang-tidy: no cxxbridge output under target/debug/build" >&2; exit 1; }

  GCC_INC="$(find "$CONDA_PREFIX/lib/gcc" -name stddef.h | head -1 | xargs dirname)"

  find qgis-sys/src -name "*.cpp" -print0 | xargs -0 --no-run-if-empty clang-tidy \
    --extra-arg="--sysroot=$CONDA_PREFIX/x86_64-conda-linux-gnu/sysroot" \
    --extra-arg="-I$GCC_INC" \
    -- -std=c++17 \
    -Iqgis-sys -Iqgis-sys/include \
    -I"$CXX_OUT/include" -I"$CXX_OUT/crate" \
    -I"$CONDA_PREFIX/include/qgis" \
    -I"$QT_INC" -I"$QT_INC/QtCore" -I"$QT_INC/QtGui" \
    -I"$QT_INC/QtWidgets" -I"$QT_INC/QtXml"
'
