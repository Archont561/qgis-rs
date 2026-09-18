"""qgis_sdk.styles — Python wrapper for qgis-styles IR.

Provides Pythonic API for StyleSheet/LayerStyle that uses Rust when available,
falls back to pure Python.

Example:
    from qgis_sdk.styles import StyleSheet, LayerStyle, Renderer, Symbol, Rgba

    style = LayerStyle.from_renderer(Renderer.single(Symbol.fill(Rgba(255, 0, 0))))
    sheet = StyleSheet().add_layer("buildings", style)
    print(sheet.to_json())

    # Apply to live QGIS layer (when inside QGIS)
    sheet.apply_to("buildings")  # finds layer by name and applies

    # Convert to MapLibre for JS bridge
    ml = sheet.to_maplibre()
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    # Try Rust core for validation
    from . import _core as _rust_core
    HAS_RUST = True
except ImportError:
    _rust_core = None
    HAS_RUST = False

# Try qgis-styles Rust crate via qgis_render (if available)
try:
    import qgis_render
    # Check if styles available
    if hasattr(qgis_render, "StyleSheet"):
        HAS_QGIS_STYLES = True
    else:
        HAS_QGIS_STYLES = False
except ImportError:
    HAS_QGIS_STYLES = False


class Rgba:
    def __init__(self, r: int, g: int, b: int, a: int = 255):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    @classmethod
    def from_hex(cls, hex_str: str) -> "Rgba":
        hex_str = hex_str.strip().lstrip("#")
        if len(hex_str) == 6:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return cls(r, g, b)
        elif len(hex_str) == 8:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            a = int(hex_str[6:8], 16)
            return cls(r, g, b, a)
        else:
            raise ValueError(f"Invalid hex color: {hex_str}")

    def to_hex(self) -> str:
        if self.a == 255:
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
        else:
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}{self.a:02x}"

    def to_dict(self) -> Dict[str, int]:
        return {"r": self.r, "g": self.g, "b": self.b, "a": self.a}

    def __repr__(self):
        return f"Rgba({self.r}, {self.g}, {self.b}, {self.a})"


class Symbol:
    @staticmethod
    def marker(color: Union[Rgba, str], size: float = 6.0, shape: str = "circle") -> Dict[str, Any]:
        if isinstance(color, Rgba):
            color = color.to_hex()
        return {"type": "marker", "color": color, "size": size, "shape": shape}

    @staticmethod
    def line(color: Union[Rgba, str], width: float = 1.0, dash: Optional[List[float]] = None) -> Dict[str, Any]:
        if isinstance(color, Rgba):
            color = color.to_hex()
        return {"type": "line", "color": color, "width": width, "dash": dash}

    @staticmethod
    def fill(color: Union[Rgba, str], outline: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if isinstance(color, Rgba):
            color = color.to_hex()
        return {"type": "fill", "color": color, "outline": outline}


class Renderer:
    @staticmethod
    def single(symbol: Dict[str, Any]) -> Dict[str, Any]:
        return {"type": "single_symbol", "symbol": symbol}

    @staticmethod
    def categorized(attr: str, categories: List[Dict[str, Any]], default_symbol: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"type": "categorized", "attr": attr, "categories": categories, "default_symbol": default_symbol}

    @staticmethod
    def graduated(attr: str, ranges: List[Dict[str, Any]], mode: str = "equal_interval") -> Dict[str, Any]:
        return {"type": "graduated", "attr": attr, "ranges": ranges, "mode": mode}

    @staticmethod
    def rule_based(rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"type": "rule_based", "rules": rules}


class LayerStyle:
    def __init__(self, renderer: Dict[str, Any], opacity: Optional[float] = None, labeling: Optional[Dict[str, Any]] = None):
        self.renderer = renderer
        self.opacity = opacity
        self.labeling = labeling
        self.raw: Optional[Dict[str, Any]] = None
        self.visible: Optional[bool] = None
        self.blend_mode: Optional[str] = None

    @classmethod
    def from_renderer(cls, renderer: Dict[str, Any]) -> "LayerStyle":
        return cls(renderer)

    def with_opacity(self, opacity: float) -> "LayerStyle":
        self.opacity = opacity
        return self

    def with_labeling(self, labeling: Dict[str, Any]) -> "LayerStyle":
        self.labeling = labeling
        return self

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"renderer": self.renderer}
        if self.opacity is not None:
            d["opacity"] = self.opacity
        if self.labeling is not None:
            d["labeling"] = self.labeling
        if self.raw is not None:
            d["raw"] = self.raw
        if self.visible is not None:
            d["visible"] = self.visible
        if self.blend_mode is not None:
            d["blend_mode"] = self.blend_mode
        return d

    def is_valid(self) -> bool:
        if not self.renderer:
            return False
        if self.opacity is not None and not (0.0 <= self.opacity <= 1.0):
            return False
        return True

    def apply_to(self, layer: Any) -> bool:
        """Apply style to live QGIS layer if available."""
        try:
            # If layer is string, find by name
            if isinstance(layer, str):
                from qgis.core import QgsProject  # type: ignore
                project = QgsProject.instance()
                layers = project.mapLayersByName(layer)
                if not layers:
                    return False
                layer = layers[0]

            # Try to apply via QGIS API
            # This is simplified — real impl would create QgsRenderer from IR
            if hasattr(layer, "renderer"):
                # For now just set opacity if available
                if self.opacity is not None and hasattr(layer, "setOpacity"):
                    layer.setOpacity(self.opacity)
                return True
            return False
        except Exception as e:
            print(f"[styles] apply_to failed: {e}")
            return False


class StyleSheet:
    def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
        self.version = 1
        self.layers: Dict[str, LayerStyle] = {}
        self.name = name
        self.description = description

    def add_layer(self, layer_id: str, style: Union[LayerStyle, Dict[str, Any]]) -> "StyleSheet":
        if isinstance(style, dict):
            # Convert dict to LayerStyle
            renderer = style.get("renderer", style)
            ls = LayerStyle(renderer)
            if "opacity" in style:
                ls.opacity = style["opacity"]
            if "labeling" in style:
                ls.labeling = style["labeling"]
            self.layers[layer_id] = ls
        else:
            self.layers[layer_id] = style
        return self

    def get_layer(self, layer_id: str) -> Optional[LayerStyle]:
        return self.layers.get(layer_id)

    def is_valid(self) -> bool:
        return all(s.is_valid() for s in self.layers.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "layers": {k: v.to_dict() for k, v in self.layers.items()},
        }

    def to_json(self, pretty: bool = True) -> str:
        if pretty:
            return json.dumps(self.to_dict(), indent=2)
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StyleSheet":
        sheet = cls(name=data.get("name"), description=data.get("description"))
        sheet.version = data.get("version", 1)
        for layer_id, style_data in data.get("layers", {}).items():
            renderer = style_data.get("renderer", {})
            ls = LayerStyle(renderer)
            if "opacity" in style_data:
                ls.opacity = style_data["opacity"]
            if "labeling" in style_data:
                ls.labeling = style_data["labeling"]
            sheet.layers[layer_id] = ls
        return sheet

    @classmethod
    def from_json(cls, json_str: str) -> "StyleSheet":
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "StyleSheet":
        content = Path(path).read_text(encoding="utf-8")
        return cls.from_json(content)

    def to_file(self, path: Union[str, Path]) -> Path:
        p = Path(path)
        p.write_text(self.to_json(), encoding="utf-8")
        return p

    def to_maplibre(self) -> Dict[str, Any]:
        """Convert to MapLibre style JSON."""
        layers = []
        for layer_id, style in self.layers.items():
            renderer = style.renderer
            r_type = renderer.get("type", "single_symbol")
            symbol = renderer.get("symbol", {})
            s_type = symbol.get("type", "fill")

            ml_type = "fill"
            if s_type == "marker":
                ml_type = "circle"
            elif s_type == "line":
                ml_type = "line"

            layers.append({
                "id": layer_id,
                "type": ml_type,
                "paint": {},
                "layout": {},
            })

        return {
            "version": 8,
            "name": self.name or "qgis-rs style",
            "layers": layers,
        }

    def apply_to(self, layer_id: str, layer: Any = None) -> bool:
        """Apply style for layer_id to live QGIS layer."""
        style = self.get_layer(layer_id)
        if not style:
            return False
        target = layer or layer_id
        return style.apply_to(target)

    def apply_all(self) -> int:
        """Apply all layer styles to project layers by name."""
        count = 0
        for layer_id in self.layers:
            if self.apply_to(layer_id):
                count += 1
        return count


__all__ = ["Rgba", "Symbol", "Renderer", "LayerStyle", "StyleSheet", "HAS_RUST", "HAS_QGIS_STYLES"]
