"""Vendor the built @archont561/qgis-sdk browser bundle into the Python package.

Run after `bun run build` in ts-packages/qgis-sdk. Copies
dist/bundle/qgis-sdk.js into src/qgis_sdk/assets/bridge/ and writes a
manifest that pins the package version and the bundle's sha256. The scaffold
links the bundle only when a WebEngine UI is selected.
"""

import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
REPO = PKG.parents[1]
SOURCE = REPO / "ts-packages" / "qgis-sdk"
TARGET = PKG / "src" / "qgis_sdk" / "assets" / "bridge"
BUNDLE_NAME = "qgis-sdk.js"


def main() -> int:
    built = SOURCE / "dist" / "bundle" / BUNDLE_NAME
    if not built.is_file():
        raise SystemExit(f"missing {built}; run `bun run build` in ts-packages/qgis-sdk first")
    package = json.loads((SOURCE / "package.json").read_text(encoding="utf-8"))

    TARGET.mkdir(parents=True, exist_ok=True)
    dest = TARGET / BUNDLE_NAME
    shutil.copyfile(built, dest)
    manifest = {
        "package": package["name"],
        "version": package["version"],
        "file": BUNDLE_NAME,
        "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
    }
    (TARGET / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"vendored {package['name']}@{package['version']} -> {dest.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
