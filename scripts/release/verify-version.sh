#!/usr/bin/env bash
# The tag, the workspace manifest and every package manifest must describe one
# release. Run before anything is built, let alone uploaded.
#
# Usage: scripts/release/verify-version.sh v1.2.3
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/../lib.sh"

tag="${1:?usage: scripts/release/verify-version.sh <vX.Y.Z>}"
version="$(pixi run -e bun version | tail -1)"

if [ "$tag" != "v$version" ]; then
  echo "tag $tag does not match workspace version $version" >&2
  exit 1
fi

# And every other manifest agrees with that one number.
pixi run -e bun version-check
echo "release $tag verified against pixi.toml [workspace] version $version"
