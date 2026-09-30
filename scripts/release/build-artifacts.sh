#!/usr/bin/env bash
# Build every immutable release asset into dist/, before a single network
# publication is attempted. A failed build is release-blocking; only the
# registry uploads that follow are allowed to fail independently.
#
#   dist/pypi/   the two maturin wheels (+ sdists)
#   dist/npm/    the npm tarballs for the addon and the bridge
#   dist/conda/  the conda packages pixi builds from the [package] manifests
#
# Usage: scripts/release/build-artifacts.sh
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/../lib.sh"

rm -rf dist
mkdir -p dist/pypi dist/npm dist/conda

echo '── Python wheels'
for dist_dir in py-packages/qgis-rs py-packages/qgis-sdk; do
  pixi run -e default bash -c '
    set -eu
    cd "$1"
    maturin build --release --out "$2"
  ' _ "$dist_dir" "$REPO_ROOT/dist/pypi"
done

echo '── npm tarballs'
# The addon has to be compiled before it can be packed: `files` lists
# qgis-rs.*.node, and pack:check is what proves it is there.
pixi run -e bun bun x turbo run build --filter=qgis-rs --filter=@qgis-sdk/bridge
pixi run -e bun bun x turbo run pack:check
for pkg in ts-packages/qgis-node ts-packages/qgis-sdk-bridge; do
  pixi run -e bun bash -c 'cd "$1" && bun pm pack --destination "$2"' _ "$pkg" "$REPO_ROOT/dist/npm"
done

echo '── conda packages'
pixi publish --target-dir dist/conda --clean

echo '── artifacts'
find dist -type f | sort
