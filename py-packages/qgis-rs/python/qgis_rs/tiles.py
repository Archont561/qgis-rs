"""Tiling helpers.

A convenience namespace — the types are defined once in :mod:`qgis_rs._api`
and re-exported here so ``from qgis_rs.tiles import TilePlan`` keeps working.
"""

from __future__ import annotations

from ._api import Tile, TilePlan, ZoomLevelPlan, ZoomRange, plan_tiles

__all__ = ["Tile", "TilePlan", "ZoomLevelPlan", "ZoomRange", "plan_tiles"]
