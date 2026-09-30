#!/usr/bin/env bash
# Generates the four files a new qgis-sys binding always needs — header, cxx
# bridge, C++ shim, module wiring — and hooks them into the parent `mod.rs` and
# `lib.rs`.
#
# Usage: scripts/scaffold.sh <layer> <concept> <QgisClass> <short_name>
# Example: scripts/scaffold.sh core geometry QgsGeometry geometry
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "$0")/lib.sh"

LAYER="${1:?usage: scripts/scaffold.sh <layer> <concept> <QgisClass> <short_name>}"
CONCEPT="${2:?missing <concept>}"
QCLASS="${3:?missing <QgisClass>}"
SHORT="${4:?missing <short_name>}"

CRATE=crates/qgis-sys
HANDLE="${QCLASS}Handle"
DIR="$CRATE/src/$LAYER/$CONCEPT"

if [ -e "$DIR/$SHORT.rs" ]; then
  echo "refusing to overwrite existing binding: $DIR/$SHORT.rs" >&2
  exit 1
fi

mkdir -p "$DIR"

cat > "$CRATE/include/$LAYER/$CONCEPT.h" <<EOF
#pragma once

#include "rust/cxx.h"
#include "qgis-sys/include/core/handle.h"

namespace qgis_shim::$LAYER {

QGIS_DECLARE_HANDLE($HANDLE);

} // namespace qgis_shim::$LAYER

#include "qgis-sys/src/$LAYER/$CONCEPT/$SHORT.rs.h"

namespace qgis_shim::$LAYER {

// TODO: declare FFI functions here

} // namespace qgis_shim::$LAYER
EOF

cat > "$DIR/$SHORT.rs" <<EOF
#[cxx::bridge(namespace = "qgis_shim::$LAYER")]
pub mod ffi {
    unsafe extern "C++" {
        include!("qgis-sys/include/$LAYER/$CONCEPT.h");

        type $HANDLE;

        // TODO: declare FFI functions here
    }
}
EOF

cat > "$DIR/$SHORT.cpp" <<EOF
#include "qgis-sys/include/$LAYER/$CONCEPT.h"
#include "qgis-sys/include/core/convert.h"

// TODO: #include <qgs....h>

// QGIS_DEFINE_HANDLE_DTOR(qgis_shim::$LAYER, $HANDLE, ::$QCLASS)

namespace {

// QGIS_HANDLE_CAST(qgis_shim::$LAYER::$HANDLE, ::$QCLASS)

} // namespace

namespace qgis_shim::$LAYER {

// TODO: implement FFI functions here

} // namespace qgis_shim::$LAYER
EOF

printf 'pub mod %s;\n' "$SHORT" > "$DIR/mod.rs"

PARENT_MOD="$CRATE/src/$LAYER/mod.rs"
grep -q "pub mod $CONCEPT;" "$PARENT_MOD" 2>/dev/null ||
  printf 'pub mod %s;\n' "$CONCEPT" >> "$PARENT_MOD"

LIB_RS="$CRATE/src/lib.rs"
ALIAS="${SHORT}_ffi"
grep -q "$ALIAS" "$LIB_RS" 2>/dev/null ||
  printf 'pub use %s::%s::%s::ffi as %s;\n' "$LAYER" "$CONCEPT" "$SHORT" "$ALIAS" >> "$LIB_RS"

cat <<EOF

✅ scaffolded $LAYER/$CONCEPT
   header:  $CRATE/include/$LAYER/$CONCEPT.h
   bridge:  $DIR/$SHORT.rs
   shim:    $DIR/$SHORT.cpp
   mod:     $DIR/mod.rs

Next steps:
  1. Edit the header — declare FFI functions
  2. Edit the .rs    — declare matching Rust signatures
  3. Edit the .cpp   — implement the functions
  4. pixi run -e default cargo build -p qgis-sys
EOF
