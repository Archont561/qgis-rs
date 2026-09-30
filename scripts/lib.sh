# Sourced by every script here; never executed directly.
#
# NOTE the name: it must not start with an underscore. .gitignore ignores `_*`
# repository-wide, so an `_common.sh` here is silently never committed and CI
# fails with "No such file or directory" on a file that exists on every
# developer's machine.
#
# One job: put the caller at the repository root and expose it as REPO_ROOT, so
# a script behaves identically whether it was started by a pixi task (cwd =
# repo root), by a package.json script (cwd = that package), by lefthook, or by
# a human from a random subdirectory.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export REPO_ROOT
cd "$REPO_ROOT"
