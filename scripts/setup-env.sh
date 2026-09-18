#!/bin/sh
# setup-env.sh — qgis-rs consumer bootstrap.
#
# Clones the env/<pack> branch from this repository, runs the
# self-extracting bundle, and writes a receipt. After this, source
# scripts/use-pack.sh (or .pixi-sandbox/activate.sh) to put tools on PATH.
#
# Usage:  sh scripts/setup-env.sh [--pack <name>] [--tag <ref>]
#
# Environment variables (override flags):
#   PIXI_SANDBOX_PACK     pack name           (default: qgis-rs)
#   PIXI_SANDBOX_TAG      branch/tag ref       (default: qgis-rs-linux-64)
#   PIXI_SANDBOX_HOME     install directory    (default: .pixi-sandbox)
#   PIXI_SANDBOX_REPO     git repo URL         (default: this repo)
#
# Exit codes: 0 ok, 2 usage, 3 unsupported platform, 4 transport failed.
#
# POSIX sh (no `local`, no bashisms).

set -eu

es_script_version="0.1.0"

# --- defaults ---------------------------------------------------------------
es_pack="${PIXI_SANDBOX_PACK:-qgis-rs}"
es_tag="${PIXI_SANDBOX_TAG:-qgis-rs-linux-64}"
es_home="${PIXI_SANDBOX_HOME:-.pixi-sandbox}"
es_repo="${PIXI_SANDBOX_REPO:-https://github.com/Archont561/qgis-rs}"
es_receipt="$es_home/env-pack-receipt.json"

# --- flags -------------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --pack) es_pack="$2"; shift 2 ;;
    --tag)  es_tag="$2";  shift 2 ;;
    --help) echo "usage: setup-env.sh [--pack NAME] [--tag REF]"; exit 0 ;;
    *) echo "setup-env: unknown flag: $1" >&2; exit 2 ;;
  esac
done

# --- platform detection ------------------------------------------------------
es_sys="$(uname -s)"
es_mach="$(uname -m)"
case "$es_sys-$es_mach" in
  Linux-x86_64 | Linux-amd64) es_platform="linux-64" ;;
  Linux-aarch64 | Linux-arm64) es_platform="linux-aarch64" ;;
  *) echo "setup-env: unsupported platform: $es_sys/$es_mach" >&2; exit 3 ;;
esac

echo "setup-env: pack=$es_pack tag=$es_tag platform=$es_platform (v$es_script_version)"

# --- fetch the env branch ----------------------------------------------------
es_branch="env/$es_tag"
es_clone="$es_home/branch-download"

echo "setup-env: cloning $es_branch from $es_repo"
rm -rf "$es_clone"
mkdir -p "$es_home"

if ! git clone --depth 1 --branch "$es_branch" "$es_repo" "$es_clone" 2>/dev/null; then
  echo "setup-env: failed to clone $es_branch" >&2
  echo "setup-env: ensure the env pack has been published (run env.yml workflow)" >&2
  exit 4
fi

# --- find and run the installer ----------------------------------------------
es_installer=""
for es_f in "$es_clone"/pixi-sandbox-*.sh "$es_clone"/qgis-rs-*.sh; do
  [ -f "$es_f" ] && { es_installer="$es_f"; break; }
done

# GitHub rejects files over 100 MB, so a large bundle is stored as
# <name>.000.part, <name>.001.part, … and must be reassembled first.
if [ ! -f "$es_installer" ]; then
  if [ -f reassemble.sh ] || ls "$es_clone"/*.000.part >/dev/null 2>&1; then
    echo "setup-env: reassembling chunked bundle"
    ( cd "$es_clone" && [ -f reassemble.sh ] && bash ./reassemble.sh )
    for es_f in "$es_clone"/pixi-sandbox-*.sh "$es_clone"/qgis-rs-*.sh; do
      [ -f "$es_f" ] && { es_installer="$es_f"; break; }
    done
  fi
fi

if [ ! -f "$es_installer" ]; then
  echo "setup-env: no self-extracting bundle found in branch" >&2
  exit 4
fi

echo "setup-env: running $(basename "$es_installer")"
# pixi-pack's executable takes -o/--output-directory and writes the environment
# into a named subdirectory of it (-e/--env-name, default "env"), so pointing it
# at $es_home with env-name "env" lands exactly where use-pack.sh looks.
es_env_dir="$es_home/env"
bash "$es_installer" -o "$es_home" -e env

# --- write receipt -----------------------------------------------------------
es_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > "$es_receipt" <<EOF
{
  "protocol": 1,
  "pack": "$es_pack",
  "version": "$es_tag",
  "platform": "$es_platform",
  "installedAt": "$es_now",
  "installDir": "$es_env_dir",
  "transport": "git:$es_repo#$es_branch",
  "tools": ["pixi", "cargo", "rustc", "clang-format", "clang-tidy"],
  "binDir": "$es_env_dir/bin",
  "setupScriptVersion": "$es_script_version"
}
EOF

echo "setup-env: environment installed to $es_env_dir"
echo "setup-env: receipt written to $es_receipt"
echo ""
echo "Next: source scripts/use-pack.sh to activate"
