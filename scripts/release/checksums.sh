#!/usr/bin/env bash
# One SHA256SUMS over every release asset, in a stable (LC_ALL=C) order so the
# file is reproducible across runners.
set -euo pipefail
# shellcheck source=scripts/_common.sh
source "$(dirname "$0")/../_common.sh"

find dist -type f -not -name SHA256SUMS -print0 |
  LC_ALL=C sort -z |
  xargs -0 sha256sum > dist/SHA256SUMS
cat dist/SHA256SUMS
