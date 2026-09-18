"""
CLI entry point for qgis-rs Python package.

This module provides `qgis-cli` and `qgis-rs` console scripts that run at
native Rust speed. Two execution paths:

1. Pure Python path using the Rust extension (`_core`) — parses args via
   Python and calls Rust library functions directly (no subprocess).

2. Binary path — if the `qgis-cli` Rust binary is on PATH (installed by the
   wheel via maturin), delegate to it for exact parity with the standalone CLI.

The default is (1) for speed and to avoid subprocess overhead; (2) is used
as fallback for commands that need QGIS backend not yet exposed via PyO3.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

try:
    from . import _core as core
    from ._core import Extent, Project, ZoomRange, TilePlan
except ImportError:
    try:
        from . import _fallback as core  # type: ignore
        from ._fallback import Extent, Project, ZoomRange, TilePlan  # type: ignore
    except ImportError:
        core = None  # type: ignore
        Extent = Project = ZoomRange = TilePlan = None  # type: ignore


def _cmd_info(args: argparse.Namespace) -> int:
    try:
        project = Project.open(str(args.project))
        info = project.info()
    except Exception as exc:
        print(f"qgis-cli: cannot open {args.project}: {exc}", file=sys.stderr)
        return 1

    if args.json:
        # Use to_dict for JSON output
        d = info.to_dict()
        print(json.dumps(d, indent=2))
    else:
        print(f"path:    {info.path}")
        print(f"format:  {info.format}")
        print(f"size:    {info.size_bytes} bytes")
        print(f"crs:     {info.crs.auth_id if info.crs else 'unknown'}")
        if info.layer_count is not None:
            print(f"layers:  {info.layer_count}")
        else:
            print(f"layers:  unknown")
        if info.note:
            print(f"note:    {info.note}")
    return 0


def _cmd_tiles(args: argparse.Namespace) -> int:
    try:
        extent = Extent.parse(args.bounds)
    except Exception as exc:
        print(f"qgis-cli: cannot read --bounds {args.bounds!r}: {exc}", file=sys.stderr)
        return 1

    try:
        zooms = ZoomRange.parse(args.zoom)
    except Exception as exc:
        print(f"qgis-cli: cannot read --zoom {args.zoom!r}: {exc}", file=sys.stderr)
        return 1

    try:
        plan = TilePlan(extent, zooms)
    except Exception as exc:
        print(f"qgis-cli: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        for level in plan.levels():
            print(
                f"z={level.zoom:<3} x {level.x_min}..{level.x_max}  "
                f"y {level.y_min}..{level.y_max}  {level.tile_count()} tiles"
            )
        print(f"Would render {plan.tile_count()} tiles across zoom levels {args.zoom}")
        return 0

    print("qgis-cli: tile rendering needs the QGIS backend, which is not wired up yet", file=sys.stderr)
    print(f"Plan would render {plan.tile_count()} tiles — use --dry-run to see breakdown", file=sys.stderr)
    return 1


def _cmd_render(args: argparse.Namespace) -> int:
    try:
        project = Project.open(str(args.project))
    except Exception as exc:
        print(f"qgis-cli: cannot open {args.project}: {exc}", file=sys.stderr)
        return 1

    try:
        # Build render settings via core if available
        # For now, delegate to Project.render which will error until QGIS backend
        rendered = project.render(
            str(args.output),
            width=args.width,
            height=args.height,
            extent=Extent.parse(args.extent) if args.extent else None,
            crs=None,
            dpi=args.dpi,
        )
        print(f"wrote {rendered.path} ({rendered.bytes} bytes)")
        return 0
    except Exception as exc:
        print(f"qgis-cli: {exc}", file=sys.stderr)
        return 1


def _cmd_version(_args: argparse.Namespace) -> int:
    if core is not None:
        print(f"qgis-rs {core.version()} (Python bindings, native speed)")
    else:
        print("qgis-rs (Python package, extension not built)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qgis-cli",
        description="Render, tile, inspect and serve QGIS projects (native Rust speed, Python API)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # info
    p_info = sub.add_parser("info", help="Describe a project")
    p_info.add_argument("project", type=Path, help="QGIS project to describe (.qgs or .qgz)")
    p_info.add_argument("--json", action="store_true", help="Print JSON instead of human-readable summary")
    p_info.set_defaults(func=_cmd_info)

    # tiles
    p_tiles = sub.add_parser("tiles", help="Build an XYZ tile pyramid (dry-run works without QGIS)")
    p_tiles.add_argument("project", type=Path, help="QGIS project to tile (.qgs or .qgz)")
    p_tiles.add_argument("-z", "--zoom", required=True, help='Zoom levels, as "12" or "10-14"')
    p_tiles.add_argument("-b", "--bounds", required=True, help='Area to cover in EPSG:4326, as "minx,miny,maxx,maxy"')
    p_tiles.add_argument("-o", "--output", type=Path, required=True, help="Output directory, or .mbtiles/.pmtiles file")
    p_tiles.add_argument("--format", default="png", help="Tile format")
    p_tiles.add_argument("--tile-size", type=int, default=256, help="Tile edge in pixels")
    p_tiles.add_argument("--parallel", type=int, default=4, help="Worker threads")
    p_tiles.add_argument("--dry-run", action="store_true", help="Count the tiles without rendering any")
    p_tiles.set_defaults(func=_cmd_tiles)

    # render
    p_render = sub.add_parser("render", help="Render a project to an image")
    p_render.add_argument("project", type=Path, help="QGIS project to render (.qgs or .qgz)")
    p_render.add_argument("-o", "--output", type=Path, required=True, help="Where to write the image")
    p_render.add_argument("--extent", help='Extent to render, as "minx,miny,maxx,maxy"')
    p_render.add_argument("--width", type=int, help="Image width in pixels")
    p_render.add_argument("--height", type=int, help="Image height in pixels")
    p_render.add_argument("--crs", help="CRS to render in, e.g. EPSG:3857")
    p_render.add_argument("--dpi", type=float, help="Resolution in dots per inch")
    p_render.add_argument("--layers", help="Comma-separated list of layers to draw")
    p_render.add_argument("--layout", help="Render a print layout instead of map canvas")
    p_render.set_defaults(func=_cmd_render)

    # version
    p_ver = sub.add_parser("version", help="Print version information")
    p_ver.set_defaults(func=_cmd_version)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Entry point for `qgis-cli` and `qgis-rs` console scripts.

    Returns an exit code (0 on success).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # If the Rust binary exists on PATH and we are invoked as binary wrapper,
    # we could delegate. But for native speed, we run Python path that uses
    # Rust extension directly (no subprocess).

    # Check extension availability
    if core is None:
        print(
            "qgis-cli: Rust extension _core not found. Install with:\n"
            "  pip install qgis-rs  # or\n"
            "  pip install maturin && maturin develop",
            file=sys.stderr,
        )
        return 1

    try:
        return args.func(args)
    except Exception as exc:
        print(f"qgis-cli: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
