#!/usr/bin/env bash
# Rust line coverage as lcov, for Codecov and for the coverage badge.
#
# `qgis-sys` is excluded: it is a thin generated FFI surface whose lines are
# attributed to C++, and instrumenting it only adds noise. `--no-default-features`
# turns PyO3's `python` feature off so the test binaries link against the
# interpreter instead of leaving extension-module symbols unresolved.
#
# No rustup component is needed: conda-forge's `rust` ships a version-matched
# llvm-profdata/llvm-cov pair in its sysroot, which is what cargo-llvm-cov
# shells out to.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"

pixi run -e default setup >/dev/null
mkdir -p target/coverage

exec pixi run -e default bash -c '
  set -eu
  QT_QPA_PLATFORM=offscreen \
  PROJ_DATA="$CONDA_PREFIX/share/proj" \
  QGIS_PLUGINPATH="$CONDA_PREFIX/lib/qgis/plugins" \
  cargo llvm-cov \
    --workspace \
    --exclude qgis-sys \
    --no-default-features \
    --lcov \
    --output-path target/coverage/rust-lcov.info \
    -- --test-threads=1
'
