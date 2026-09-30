#!/usr/bin/env bash
# GitHub Packages is a separate npm registry and does not implement npmjs
# Trusted Publishing, so it needs the workflow token. The token is written to a
# throwaway npmrc rather than the user config: it must never end up applied to
# the npmjs upload, which mints its own short-lived OIDC credential and would
# silently prefer a static token if one were present.
#
# Requires NODE_AUTH_TOKEN and RUNNER_TEMP.
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/../lib.sh"

: "${NODE_AUTH_TOKEN:?NODE_AUTH_TOKEN is not set}"
config="${RUNNER_TEMP:-/tmp}/github-packages.npmrc"
cat >"$config" <<'NPMRC'
@archont561:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${NODE_AUTH_TOKEN}
NPMRC

for tarball in dist/npm/*.tgz; do
  NPM_CONFIG_USERCONFIG="$config" npm publish --registry https://npm.pkg.github.com "$tarball"
done
