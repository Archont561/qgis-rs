#!/usr/bin/env bash
# taplo canonicality check. Only pixi.toml and .pixi-sandbox.toml are kept in
# taplo's canonical form — the rest of the repo uses the aligned-`=` style on
# purpose — so a bare run checks exactly those two. Arguments (staged files
# from lefthook) override that list.
set -euo pipefail
# shellcheck source=scripts/_common.sh
source "$(dirname "$0")/_common.sh"

if [ "$#" -gt 0 ]; then
  taplo fmt --check "$@"
else
  taplo fmt --check pixi.toml .pixi-sandbox.toml
fi
