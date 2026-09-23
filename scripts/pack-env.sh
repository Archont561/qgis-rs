#!/bin/sh
# pack-env.sh — bundle a pixi environment into a self-extracting pack and prove
# it works, so a machine without access to conda-forge/prefix.dev/rust-lang.org
# can still bootstrap the toolchain (see .knowledge/env-provisioning.md).
#
# Single implementation shared by `pixi run pack` and .github/workflows/env.yml.
#
# Usage:
#   pixi run pack                                   # dev env, dist/
#   sh scripts/pack-env.sh -e docs -o dist --no-smoke
#
# The environment must contain pixi-pack (declared in [workspace.dependencies]);
# run `pixi lock` after changing that pin.
set -eu

pe_env="dev"
pe_out="dist"
pe_smoke=1
pe_manifest="pixi.toml"

while [ $# -gt 0 ]; do
  case "$1" in
    -e|--environment) pe_env="$2"; shift 2 ;;
    -o|--output)      pe_out="$2"; shift 2 ;;
    -m|--manifest)    pe_manifest="$2"; shift 2 ;;
    --no-smoke)       pe_smoke=0; shift ;;
    -h|--help)
      sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "pack-env: unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ ! -f "$pe_manifest" ]; then
  echo "pack-env: manifest not found: $pe_manifest (run from the repository root)" >&2
  exit 2
fi

if ! command -v pixi-pack >/dev/null 2>&1; then
  echo "pack-env: pixi-pack is not on PATH." >&2
  echo "pack-env: run it inside the environment — 'pixi run -e $pe_env pack' —" >&2
  echo "pack-env: or 'pixi global install pixi-pack'." >&2
  exit 3
fi

# linux-64 today; pixi reports the host platform, which is what the branch and
# artifact names are keyed on.
pe_platform="${PIXI_SANDBOX_PLATFORM:-linux-64}"
case "$pe_env" in
  dev) pe_name="qgis-rs-$pe_platform" ;;
  *)   pe_name="qgis-rs-$pe_env-$pe_platform" ;;
esac

mkdir -p "$pe_out"
echo "pack-env: packing environment '$pe_env' -> $pe_out/$pe_name.sh"
pixi-pack \
  --environment "$pe_env" \
  --create-executable \
  --output "$pe_out/$pe_name" \
  "$pe_manifest"

if [ ! -f "$pe_out/$pe_name.sh" ]; then
  echo "pack-env: expected $pe_out/$pe_name.sh was not produced" >&2
  exit 4
fi
ls -lh "$pe_out/$pe_name.sh"

if [ "$pe_smoke" -eq 0 ]; then
  echo "pack-env: smoke test skipped"
  exit 0
fi

# A self-extracting pixi-pack takes -o/--output-directory plus -e/--env-name:
# the environment lands in <output>/<env-name>, which is exactly where
# scripts/use-pack.sh looks after setup-env.sh unpacks it.
pe_tmp="$(mktemp -d)"
trap 'rm -rf "$pe_tmp"' EXIT INT TERM

echo "pack-env: unpacking into a scratch directory to verify"
bash "$pe_out/$pe_name.sh" -o "$pe_tmp" -e env

for pe_tool in pixi cargo rustc bun; do
  if [ -x "$pe_tmp/env/bin/$pe_tool" ]; then
    printf 'pack-env:   %-6s ' "$pe_tool"
    "$pe_tmp/env/bin/$pe_tool" --version 2>/dev/null | head -1 || echo "(--version failed)"
  fi
done

du -sh "$pe_tmp/env" "$pe_out/$pe_name.sh"

cat <<EOF

pack-env: ok — bundle at $pe_out/$pe_name.sh
  publish it with:  sh scripts/publish-env-branch.sh $pe_name $pe_out
  consume it with:  git clone --depth 1 --branch env/$pe_name <repo> pack
                    sh scripts/setup-env.sh
                    . scripts/use-pack.sh
EOF
