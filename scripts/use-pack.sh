#!/bin/sh
# use-pack.sh — put an unpacked env pack's toolchain on PATH for this shell.
#
# Usage (must be SOURCED, not executed):
#
#     . scripts/use-pack.sh
#
# After sourcing, pixi, cargo, rustc, clang-format, clang-tidy resolve from
# the pack unpacked into $PIXI_SANDBOX_HOME (default: .pixi-sandbox/).
#
# Obtain the pack first:
#   sh scripts/setup-env.sh
#
# POSIX sh (no `local`); variables are prefixed `up_`.
# Deliberately NOT `set -eu`: this file is sourced.

# Root of the unpacked pack
if [ -n "${PIXI_SANDBOX_HOME:-}" ]; then
    up_root="$PIXI_SANDBOX_HOME"
elif [ -d "${PWD}/.pixi-sandbox/env/bin" ]; then
    up_root="${PWD}/.pixi-sandbox"
else
    up_root=""
fi

if [ -z "$up_root" ] || [ ! -d "$up_root/env/bin" ]; then
    echo "use-pack: no unpacked pack found." >&2
    echo "use-pack: run 'sh scripts/setup-env.sh' first, or set PIXI_SANDBOX_HOME." >&2
else
    # Prepend once; sourcing repeatedly must not grow PATH.
    case ":${PATH}:" in
        *":$up_root/env/bin:"*) ;;
        *) PATH="$up_root/env/bin:$PATH" ;;
    esac
    export PATH

    # Conda activation — set CONDA_PREFIX so build.rs finds Qt/QGIS.
    CONDA_PREFIX="$up_root/env"
    CONDA_SHLVL=1
    export CONDA_PREFIX CONDA_SHLVL

    # Run conda activation hooks (sysroot, lib paths, etc.)
    for up_hook in "$up_root"/env/etc/conda/activate.d/*.sh; do
        [ -r "$up_hook" ] || continue
        . "$up_hook" >/dev/null 2>&1 || true
    done

    # qgis-rs specific: symlink libqca if needed
    if [ -f "$up_root/env/lib/libqca-qt6.so.2" ] && \
       [ ! -f "$up_root/env/lib/libqca-qt5.so.2" ]; then
        ln -sf libqca-qt6.so.2 "$up_root/env/lib/libqca-qt5.so.2" 2>/dev/null || true
    fi

    echo "use-pack: activated ($up_root/env/bin on PATH)"
    echo "use-pack: CONDA_PREFIX=$CONDA_PREFIX"
fi

unset up_root up_hook
