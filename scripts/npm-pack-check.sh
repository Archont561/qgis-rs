#!/usr/bin/env bash
# Asserts the npm package actually contains everything its `files` list
# promises, before `npm publish` finds out for us in a way that cannot be
# unpublished.
#
# Usage: scripts/npm-pack-check.sh <package-dir> <required...>
# A required entry ending in `/` is checked as a directory; an entry containing
# `*` is checked as a glob that must match at least once.
set -euo pipefail
# shellcheck source=scripts/_common.sh
source "$(dirname "$0")/_common.sh"

pkg_dir="${1:?usage: scripts/npm-pack-check.sh <package-dir> <required...>}"
shift
cd "$pkg_dir"

fail=0
for entry in "$@"; do
  case "$entry" in
    */)
      [ -d "${entry%/}" ] || { echo "missing from package: $entry" >&2; fail=1; }
      ;;
    *'*'*)
      # shellcheck disable=SC2086
      set -- $entry
      [ -e "$1" ] || { echo "missing from package: $entry (did the build run?)" >&2; fail=1; }
      ;;
    *)
      [ -e "$entry" ] || { echo "missing from package: $entry" >&2; fail=1; }
      ;;
  esac
done

[ "$fail" = 0 ] || exit 1
echo "package contents verified in $pkg_dir"
