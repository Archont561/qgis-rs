"""Deprecated `qgis-rs` console script: prints a notice, then runs `qgis_py.cli`."""

import sys
from typing import List, Optional

from qgis_py import cli as _cli


def main(argv: Optional[List[str]] = None) -> int:
    print("qgis-rs is renamed qgis-py; use the `qgis-py` command instead", file=sys.stderr)
    return _cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
