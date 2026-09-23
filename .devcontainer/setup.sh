#!/usr/bin/env bash
# Install OpenCode for the non-root devcontainer user and refresh its model catalog.
set -euo pipefail

# Devcontainer lifecycle commands run in non-login shells. Load the Node feature's
# nvm environment so npm uses its Node 22 installation rather than any system Node.
nvm_dir="${NVM_DIR:-/usr/local/share/nvm}"
if [ -s "$nvm_dir/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$nvm_dir/nvm.sh"
  nvm use --silent default
fi

pixi --version
node --version
npm --version

# Keep the CLI reproducible. Bump this version deliberately when updating it;
# the model catalog is refreshed independently of the installed CLI version.
npm install --global --no-audit --no-fund opencode-ai@1.18.32
opencode --version

# Refreshing needs access to the model catalog, not provider credentials. OpenCode
# may fall back to its bundled list even when the fetch fails, so don't claim a
# successful download merely because the command exits successfully. Suppress
# its own "Models cache refreshed" banner, which can appear even on fallback.
if opencode models --refresh >/dev/null 2>&1; then
  echo "OpenCode model refresh attempted; rerun 'opencode models --refresh' if offline."
else
  echo "OpenCode model refresh unavailable; rerun 'opencode models --refresh' when online." >&2
fi
