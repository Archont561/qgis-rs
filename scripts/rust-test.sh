#!/usr/bin/env bash
# The Rust suites. Two shapes, because they need different amounts of QGIS:
#
#   --fast (default)  everything that does not need a QGIS runtime: every
#                     crate's tests/ except qgis-sys's QGIS-backed pair, plus
#                     qgis-sys's own headless smoke suite. Needs only the
#                     libqca link.
#   --full            the QGIS-backed suites; additionally needs PROJ data and
#                     the QGIS plugin path pointed at the conda prefix
#
# `--fast` used to run `--test application_info` alone, which meant the pre-push
# loop compiled 120 tests and ran five of them; the rest were only reached by
# the coverage step, which `pixi run gates` skips.
#
# Both force `--test-threads=1`: QgsApplication is a process-global singleton
# and parallel test threads race its lifecycle.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"

mode=fast
case "${1-}" in
  --fast) shift ;;
  --full) mode=full; shift ;;
esac

# Repairs the libqca soname QGIS still asks for. Cheap and idempotent.
pixi run -e default setup >/dev/null

if [ "$mode" = full ]; then
  exec pixi run -e default bash -c '
    set -eu
    PROJ_DATA="$CONDA_PREFIX/share/proj" \
    QGIS_PLUGINPATH="$CONDA_PREFIX/lib/qgis/plugins" \
    QT_QPA_PLATFORM=offscreen \
    cargo test --workspace --no-default-features \
      --test application_lifecycle --test vector_layer \
      "$@" -- --test-threads=1
  ' _ "$@"
fi

exec pixi run -e default bash -c '
  set -eu
  # Everything but qgis-sys: pure Rust, no QGIS runtime, a second or two.
  # --no-default-features keeps PyO3 '"'"'s extension-module off so the test
  # binaries link against the interpreter instead of leaving its symbols
  # unresolved.
  QT_QPA_PLATFORM=offscreen \
  cargo test --workspace --exclude qgis-sys --no-default-features \
    "$@" -- --test-threads=1

  # qgis-sys links real QGIS, so only its smoke suite belongs in the fast loop;
  # application_lifecycle and vector_layer need the --full environment.
  QT_QPA_PLATFORM=offscreen \
  cargo test -p qgis-sys --no-default-features \
    --test application_info \
    "$@" -- --test-threads=1
' _ "$@"
