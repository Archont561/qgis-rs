#!/usr/bin/env bash
# Install OpenCode for the non-root devcontainer user and refresh its model catalog.
set -euo pipefail

# No Node.js in this devcontainer. OpenCode itself is an npm package, so it is
# installed with bun out of the `bun` pixi environment, which is the only
# JavaScript runtime in the project (see the header of pixi.toml for why QGIS
# and bun cannot share an environment). Installing into BUN_INSTALL rather than
# the pixi prefix keeps `opencode` on PATH for ordinary shells, not just
# `pixi run` ones.
export BUN_INSTALL="$HOME/.bun"
mkdir -p "$BUN_INSTALL/bin"

pixi --version
pixi run -e bun bun --version

# Keep the CLI reproducible. Bump this version deliberately when updating it;
# the model catalog is refreshed independently of the installed CLI version.
pixi run -e bun env BUN_INSTALL="$BUN_INSTALL" bun install --global --no-audit --no-fund opencode-ai@1.18.32

# Put the bun global bin directory on PATH for future shells. bashrc is the
# right file for an interactive login-less devcontainer shell; bash_profile
# would be skipped by shells started without a login flag.
grep -q 'HOME/.bun/bin' "$HOME/.bashrc" 2>/dev/null ||
  printf '\nexport PATH="$HOME/.bun/bin:$PATH"\n' >>"$HOME/.bashrc"
export PATH="$BUN_INSTALL/bin:$PATH"

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
