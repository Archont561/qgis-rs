#!/usr/bin/env bash
# Publish the Rust crates to crates.io in dependency order.
#
# Two things make this more than a loop:
#
#  1. crates.io index propagation. A dependent crate can be rejected seconds
#     after its dependency was accepted, because the index has not caught up —
#     so each upload is retried with a backoff.
#  2. Immutable duplicates. An earlier, partially successful release attempt
#     leaves some crates already published. That must not block the rest, so a
#     rejection whose cause is "already exists" is a warning, not a failure.
#
# Requires CARGO_REGISTRY_TOKEN in the environment.
set -euo pipefail
# shellcheck source=scripts/_common.sh
source "$(dirname "$0")/../_common.sh"

: "${CARGO_REGISTRY_TOKEN:?CARGO_REGISTRY_TOKEN is not set}"

# Dependency order. qgis-py / qgis-sdk / qgis-node are deliberately absent:
# they are PyO3 and NAPI cores whose only consumers are the wheels and the npm
# package built from this same tag, and a crates.io copy of an extension module
# is a download nobody can link against.
CRATES=(qgis-sys qgis-styles qgis-render qgis-server qgis-mcp qgis-cli)

publish_one() {
  local crate="$1" attempt output
  for attempt in 1 2 3 4 5 6; do
    if output="$(pixi run -e default cargo publish --locked --package "$crate" 2>&1)"; then
      echo "$output"
      echo "published $crate"
      return 0
    fi
    echo "$output"
    if grep -qi 'already .*uploaded\|already exists' <<<"$output"; then
      echo "::warning title=$crate was not uploaded::already on crates.io from an earlier attempt; continuing"
      return 0
    fi
    echo "attempt $attempt for $crate failed; waiting for index propagation"
    sleep $((attempt * 15))
  done
  echo "giving up on $crate" >&2
  return 1
}

for crate in "${CRATES[@]}"; do
  publish_one "$crate"
done
