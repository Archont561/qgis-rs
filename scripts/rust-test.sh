#!/usr/bin/env bash
# The Rust suites. Two shapes, because they need different amounts of QGIS:
#
#   --fast (default)  the headless smoke suite; needs only the libqca link
#   --full            the QGIS-backed suites; additionally needs PROJ data and
#                     the QGIS plugin path pointed at the conda prefix
#
# Both force `--test-threads=1`: QgsApplication is a process-global singleton
# and parallel test threads race its lifecycle.
set -euo pipefail
# shellcheck source=scripts/_common.sh
source "$(dirname "$0")/_common.sh"

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
  QT_QPA_PLATFORM=offscreen \
  cargo test --workspace --no-default-features \
    --test application_info \
    "$@" -- --test-threads=1
' _ "$@"
