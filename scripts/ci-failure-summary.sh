#!/usr/bin/env bash
# Turn a failed gate log into something a reviewer can read without opening the
# UI: the interesting lines land in the job summary AND in a GitHub annotation,
# which is the only part of a run the REST API hands back in full.
#
# Usage: scripts/ci-failure-summary.sh gate.log
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"

log="${1:?usage: scripts/ci-failure-summary.sh <log>}"

# Lines that name a cause, rather than the thousands that name a passing test.
interesting() {
  grep -n -E \
    'FAILED|^E |error:|ERROR|Error:|assert |panicked|ImportError|ModuleNotFound|native extension:|package resolved from:|not properly formatted|unformatted files|Failed:' \
    "$log" || true
}

{
  echo '### CI gate failed'
  echo
  echo '#### Lines that name a cause'
  echo '```'
  interesting | tail -n 80
  echo '```'
  echo
  echo '#### Last 200 lines'
  echo '```'
  tail -n 200 "$log"
  echo '```'
} >> "${GITHUB_STEP_SUMMARY:-/dev/stdout}"

# One annotation, newline-encoded per the workflow-command format.
encoded="$( { interesting | tail -n 60; echo '--- tail ---'; tail -n 60 "$log"; } |
  sed -e 's/%/%25/g' -e 's/\r/%0D/g' | awk '{ printf "%s%%0A", $0 }')"
printf '::error title=CI gate failed::%s\n' "$encoded"
