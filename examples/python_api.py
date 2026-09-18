#!/usr/bin/env python3
"""
Example: using qgis-rs Python API at native Rust speed.

Install:
    pip install qgis-rs
    # or for dev:
    # pip install maturin && maturin develop --manifest-path packages/qgis-rs/Cargo.toml

Run:
    python examples/python_api.py
"""

from pathlib import Path
import tempfile

# Import qgis_rs — will use Rust _core if built, else pure-Python fallback
import qgis_rs

print(f"qgis-rs version: {qgis_rs.__version__}")
print(f"Using fallback: {qgis_rs._USING_FALLBACK}")
print()

# 1. Extent parsing (pure Rust, no QGIS)
print("=== Extent ===")
extent = qgis_rs.Extent.parse("14,50,15,51")
print(f"Parsed: {extent}")
print(f"Width: {extent.width()}, Height: {extent.height()}")
print(f"Contains 14.5,50.5: {extent.contains(14.5, 50.5)}")
print()

# 2. CRS handling (pure Rust)
print("=== CRS ===")
crs_4326 = qgis_rs.Crs.from_epsg(4326)
crs_3857 = qgis_rs.Crs.from_epsg(3857)
print(f"4326: {crs_4326.auth_id}, geographic={crs_4326.is_geographic()}")
print(f"3857: {crs_3857.auth_id}, projected={crs_3857.is_projected()}")
print()

# 3. Tile planning (pure Rust, native speed)
print("=== Tile planning (pure Rust, no QGIS) ===")
zooms = qgis_rs.ZoomRange.parse("10-14")
plan = qgis_rs.TilePlan(extent, zooms)
print(f"Bounds: {plan.bounds}")
print(f"Zooms: {plan.zooms.min}-{plan.zooms.max}")
print(f"Total tiles: {plan.tile_count()}")
for level in plan.levels():
    print(f"  z={level.zoom}: x {level.x_min}..{level.x_max}, y {level.y_min}..{level.y_max}, {level.tile_count()} tiles")

# Fast function variant
total, levels = qgis_rs.plan_tiles("14,50,15,51", "10-14")
print(f"\nplan_tiles() fast path: {total} tiles")
print()

# 4. Project handling (path check, no QGIS needed for info)
print("=== Project ===")
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp) / "map.qgs"
    tmp_path.write_text("<qgis></qgis>")
    project = qgis_rs.Project.open(str(tmp_path))
    print(f"Opened: {project.path}, format={project.format}")
    info = project.info()
    print(f"Info: {info.to_dict()}")
    print()

# 5. CLI via Python (same Rust logic)
print("=== CLI via Python (native speed) ===")
from qgis_rs.cli import main as cli_main

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp) / "map.qgs"
    tmp_path.write_text("<qgis></qgis>")
    print("$ qgis-cli info map.qgs")
    cli_main(["info", str(tmp_path)])
    print()
    print("$ qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 -o ./tiles --dry-run")
    cli_main(["tiles", str(tmp_path), "-z", "10-14", "-b", "14,50,15,51", "-o", "./tiles", "--dry-run"])

print("\nDone — for full rendering, install QGIS: conda install -c conda-forge qgis qgis-rs")
