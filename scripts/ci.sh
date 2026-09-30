#!/usr/bin/env bash
# The one gate. `pixi run ci` locally and the CI workflow both run exactly this
# file, so "passes on my machine" and "passes in Actions" cannot mean different
# things.
#
# Order is deliberate: the cheap repo-wide lints fail in seconds, the format
# gate fails before any compile, and only then does turbo fan out the package
# suites. Coverage runs last because it is the most expensive producer and its
# artifacts are only interesting once everything else is green.
#
# Usage: scripts/ci.sh [--no-coverage]
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"

coverage=1
for arg in "$@"; do
  case "$arg" in
    --no-coverage) coverage=0 ;;
    *) echo "scripts/ci.sh: unknown argument: $arg" >&2; exit 2 ;;
  esac
done

# The docs site is excluded everywhere below: it is built and deployed by
# docs.yml, and pulling Astro into the gate would double the critical path for
# a surface that cannot break the libraries.
readonly NOT_DOCS='--filter=!qgis-rs-docs'

step() { printf '\n\033[1m── %s\033[0m\n' "$*"; }

step 'repo lints (taplo, actionlint)'
pixi run -e default lint-toml
pixi run -e default lint-actions

step 'package lints (turbo fan-out)'
pixi run -e bun bun x turbo run lint "$NOT_DOCS"

step 'format drift gate'
pixi run -e bun bun x turbo run format "$NOT_DOCS"
if ! git diff --exit-code --quiet; then
  echo 'unformatted files — run `bun x turbo run format` and commit the result' >&2
  git --no-pager diff --stat >&2
  exit 1
fi

step 'tests (turbo fan-out; each package builds what it needs)'
pixi run -e bun bun x turbo run test "$NOT_DOCS"

step 'publishable-package contents'
pixi run -e bun bun x turbo run pack:check

if [ "$coverage" = 1 ]; then
  step 'coverage (rust lcov + python xml + js)'
  pixi run -e bun bun x turbo run coverage "$NOT_DOCS"
fi

step 'gate passed'
