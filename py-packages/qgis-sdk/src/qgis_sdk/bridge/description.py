"""qgis_sdk.bridge.description — Bridge description without codegen.

Instead of generating TS files, we introspect Python bridge class and produce
a JSON description that JS can load at runtime via window.__QGIS_BRIDGE_DESCRIPTION__.

This allows:
- No codegen step needed for dev
- JS creates methods dynamically from description
- Optional codegen for static typing via `qgis-plugin bridge describe --output bridge.json`
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Type, get_type_hints


@dataclass
class MethodDescription:
    name: str
    args: List[str] = field(default_factory=list)
    arg_types: List[str] = field(default_factory=list)
    return_type: str = "any"
    doc: str = ""
    is_signal: bool = False
    is_slot: bool = True
    is_property: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MethodDescription":
        return cls(**data)


@dataclass
class BridgeDescription:
    name: str
    methods: List[MethodDescription] = field(default_factory=list)
    signals: List[MethodDescription] = field(default_factory=list)
    properties: List[MethodDescription] = field(default_factory=list)
    version: str = "1.0"
    doc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "doc": self.doc,
            "methods": [m.to_dict() for m in self.methods],
            "signals": [s.to_dict() for s in self.signals],
            "properties": [p.to_dict() for p in self.properties],
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_json_dict(self) -> Dict[str, Any]:
        return self.to_dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BridgeDescription":
        methods = [MethodDescription.from_dict(m) for m in data.get("methods", [])]
        signals = [MethodDescription.from_dict(s) for s in data.get("signals", [])]
        properties = [MethodDescription.from_dict(p) for p in data.get("properties", [])]
        return cls(
            name=data.get("name", "bridge"),
            methods=methods,
            signals=signals,
            properties=properties,
            version=data.get("version", "1.0"),
            doc=data.get("doc", ""),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "BridgeDescription":
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_class(cls, py_cls: Type, name: Optional[str] = None) -> "BridgeDescription":
        """Introspect Python class to create description."""
        bridge_name = name or getattr(py_cls, "_bridge_name", py_cls.__name__.lower())
        doc = inspect.getdoc(py_cls) or ""

        methods: List[MethodDescription] = []
        signals: List[MethodDescription] = []
        properties: List[MethodDescription] = []

        # Get type hints for class
        try:
            class_hints = get_type_hints(py_cls)
        except Exception:
            class_hints = {}

        for attr_name in dir(py_cls):
            if attr_name.startswith("_"):
                continue
            try:
                attr = getattr(py_cls, attr_name)
            except Exception:
                continue

            # Check if marked via decorators
            is_bridge_method = getattr(attr, "_is_bridge_method", False)
            is_signal = getattr(attr, "_is_signal", False)
            is_slot = getattr(attr, "_is_slot", False)
            is_prop = getattr(attr, "_is_bridge_property", False)

            # If not explicitly marked, include public callables (except class)
            if not (is_bridge_method or is_signal or is_slot or is_prop):
                if not callable(attr):
                    # Check property
                    if isinstance(attr, property):
                        # Treat as property
                        is_prop = True
                    else:
                        continue
                if inspect.isclass(attr):
                    continue
                # Skip if it's inherited from object etc
                # We include it as method by default for backwards compat
                # But skip private and dunder
                pass

            try:
                sig = inspect.signature(attr)
            except (ValueError, TypeError):
                # For properties, no sig
                if is_prop:
                    sig = None
                else:
                    continue

            # Get method hints
            try:
                hints = get_type_hints(attr)
            except Exception:
                hints = {}

            args: List[str] = []
            arg_types: List[str] = []
            return_type = "any"
            method_doc = inspect.getdoc(attr) or getattr(attr, "_bridge_doc", "") or ""

            if sig:
                params = [p for p in sig.parameters.values() if p.name not in ("self", "cls")]
                for p in params:
                    args.append(p.name)
                    # Resolve type
                    param_hint = hints.get(p.name, class_hints.get(p.name, None))
                    if param_hint is not None:
                        arg_types.append(_type_to_str(param_hint))
                    else:
                        # Try annotation directly
                        ann = p.annotation
                        if ann != inspect.Parameter.empty:
                            arg_types.append(_type_to_str(ann))
                        else:
                            arg_types.append("any")

                # Return type
                ret_hint = hints.get("return", None)
                if ret_hint is not None:
                    return_type = _type_to_str(ret_hint)
                else:
                    # Check _return_type attr from decorator
                    rt = getattr(attr, "_return_type", None) or getattr(attr, "_bridge_return_type", None)
                    if rt is not None:
                        return_type = _type_to_str(rt)
                    else:
                        # Try signature return annotation
                        if sig.return_annotation != inspect.Signature.empty:
                            return_type = _type_to_str(sig.return_annotation)

            # Explicit decorator overrides
            if getattr(attr, "_bridge_return_type", None):
                return_type = _type_to_str(getattr(attr, "_bridge_return_type"))

            desc = MethodDescription(
                name=attr_name,
                args=args,
                arg_types=arg_types,
                return_type=return_type,
                doc=method_doc,
                is_signal=bool(is_signal),
                is_slot=bool(is_slot) if (is_slot or is_bridge_method) else True,
                is_property=bool(is_prop),
            )

            if is_signal:
                signals.append(desc)
            elif is_prop:
                properties.append(desc)
            else:
                methods.append(desc)

        return cls(
            name=bridge_name,
            methods=methods,
            signals=signals,
            properties=properties,
            version=getattr(py_cls, "_bridge_version", "1.0"),
            doc=doc,
        )


def _type_to_str(py_type: Any) -> str:
    """Convert Python type to string for JSON description."""
    if py_type is None:
        return "void"
    if isinstance(py_type, str):
        return py_type
    # Handle actual types
    try:
        # If it's a type, get name
        if isinstance(py_type, type):
            name = py_type.__name__
            mapping = {
                "str": "string",
                "int": "number",
                "float": "number",
                "bool": "boolean",
                "dict": "object",
                "list": "array",
                "NoneType": "void",
                "None": "void",
            }
            return mapping.get(name, name)
        # For typing constructs
        origin = getattr(py_type, "__origin__", None)
        args = getattr(py_type, "__args__", None)
        type_str = str(py_type)
        # Simplify
        if "Optional" in type_str or (args and len(args) == 2 and args[1] is type(None)):
            # Optional[X] -> X | null
            if args:
                non_none = [a for a in args if a is not type(None)]
                if non_none:
                    return _type_to_str(non_none[0])
        if origin is not None:
            if origin is list or "List" in str(origin) or "list" in str(origin).lower():
                if args:
                    inner = _type_to_str(args[0])
                    return f"{inner}[]"
                return "array"
            if origin is dict or "Dict" in str(origin):
                return "object"
        # Fallback to string representation cleaned
        # e.g. "<class 'str'>" -> "string"
        # Use repr
        return type_str.replace("typing.", "").replace("<class '", "").replace("'>", "")
    except Exception:
        return "any"


# Registry for bridge descriptions
class BridgeRegistry:
    def __init__(self):
        self._descriptions: Dict[str, BridgeDescription] = {}
        self._classes: Dict[str, Type] = {}

    def register(self, description: BridgeDescription, cls: Type):
        self._descriptions[description.name] = description
        self._classes[description.name] = cls

    def get(self, name: str) -> Optional[BridgeDescription]:
        return self._descriptions.get(name)

    def get_class(self, name: str) -> Optional[Type]:
        return self._classes.get(name)

    def all(self) -> Dict[str, BridgeDescription]:
        return dict(self._descriptions)

    def clear(self):
        self._descriptions.clear()
        self._classes.clear()


# Global registry
bridge_registry = BridgeRegistry()
