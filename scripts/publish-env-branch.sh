#!/bin/sh
# publish-env-branch.sh — force-push dist/ to an orphan env/<pack> branch.
#
# Usage:  sh scripts/publish-env-branch.sh <pack-slug> <dist-dir>
# Example: sh scripts/publish-env-branch.sh qgis-rs-linux-64 dist
#
# POSIX sh; set -eu. Called from CI with contents: write permission.

set -eu

pb_pack="${1:?usage: publish-env-branch.sh <pack-slug> <dist-dir>}"
pb_dist="${2:?usage: publish-env-branch.sh <pack-slug> <dist-dir>}"
pb_branch="env/$pb_pack"

[ -d "$pb_dist" ] || { echo "publish-env-branch: $pb_dist is not a directory" >&2; exit 1; }

pb_work="$(mktemp -d)"
trap 'rm -rf "$pb_work"' EXIT

git init -q -b "$pb_branch" "$pb_work"
cd "$pb_work"

cp -r "$OLDPWD/$pb_dist"/* .

cat > README.md <<EOF
# env/$pb_pack

Self-extracting environment pack for qgis-rs (linux-64).

## Usage

\`\`\`sh
git clone --depth 1 --branch $pb_branch \\
  https://github.com/Archont561/qgis-rs pack
cd pack && bash ./pixi-sandbox-*.sh
. scripts/use-pack.sh
cargo --version && pixi --version
\`\`\`

Built from: \`$GITHUB_SHA\`
Published: $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

git add -A
git -c user.name="env-bot" -c user.email="env-bot@noreply" \
  commit -q -m "env: $pb_pack from $GITHUB_SHA"
git push -f origin "HEAD:refs/heads/$pb_branch"

echo "publish-env-branch: pushed $pb_branch"
