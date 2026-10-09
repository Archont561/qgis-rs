"""Build qgis-cli for this machine and stage it where the qgis-py wheel picks it up.

Release builds run this before `maturin build`, so each platform's wheel carries
the binary built on that platform's runner. Nothing is compiled on the user's
machine. The binary links QGIS, so this needs the default pixi environment.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parents[1]
DEST = PKG / "python" / "qgis_py" / "_bin"


def main() -> int:
    build = subprocess.run(["cargo", "build", "--release", "-p", "qgis-cli"], cwd=REPO)
    if build.returncode != 0:
        return build.returncode
    exe = "qgis-cli.exe" if sys.platform == "win32" else "qgis-cli"
    source = REPO / "target" / "release" / exe
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    target = DEST / exe
    shutil.copyfile(source, target)
    os.chmod(target, 0o755)
    print(f"staged {exe} in {target.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
