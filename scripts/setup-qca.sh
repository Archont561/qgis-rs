#!/usr/bin/env bash
# QGIS still dlopens libqca under its Qt5 soname, whichever flavour conda-forge
# installed. Link whatever is present to the name QGIS asks for; idempotent, so
# every task that needs a live QGIS can call it unconditionally.
set -euo pipefail
L="${CONDA_PREFIX:?run me under pixi}/lib"
if [ -e "$L/libqca-qt6.so.2" ]; then
  ln -sf "$L/libqca-qt6.so.2" "$L/libqca-qt5.so.2"
elif [ -e "$L/libqca-qt5.so.2.3.12" ]; then
  ln -sf libqca-qt5.so.2.3.12 "$L/libqca-qt5.so.2"
else
  echo "no libqca found under $L" >&2
  exit 1
fi
