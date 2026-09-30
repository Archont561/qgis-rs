#!/usr/bin/env bash
# cargo build for the whole Cargo workspace, inside the QGIS-activated env.
# Extra arguments are appended to cargo (e.g. `-p qgis-sys`).
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"
exec pixi run -e default cargo build --release "$@"
