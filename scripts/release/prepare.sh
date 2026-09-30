#!/usr/bin/env bash
# Derive the next version from the conventional-commit history, write it into
# every manifest, regenerate the changelog, and refresh the lockfiles that
# embed a version. Called by .github/workflows/autorelease.yml; runnable
# locally to preview exactly what that workflow would commit.
#
# Usage: scripts/release/prepare.sh [X.Y.Z]
# With no argument, convco picks the bump from the commits since the last tag.
set -euo pipefail
# shellcheck source=scripts/_common.sh
source "$(dirname "$0")/../_common.sh"

next="${1-}"
if [ -z "$next" ]; then
  next="$(pixi run -e default convco version --bump | tail -1)"
fi
[ -n "$next" ] || { echo "convco produced no version" >&2; exit 1; }

if git rev-parse --verify --quiet "refs/tags/v${next}" >/dev/null; then
  echo "v${next} already exists; there are no releasable commits" >&2
  exit 1
fi

echo "preparing v${next}"
pixi run -e bun version-set "$next"
pixi run -e default convco changelog --unreleased "$next" --output CHANGELOG.md

# The lockfiles embed the workspace member versions that just changed.
pixi run -e bun bun install --lockfile-only
pixi run -e default cargo metadata --format-version 1 >/dev/null
pixi lock

# Nothing is committed until every manifest agrees on the new number.
pixi run -e bun version-check

echo "$next"
