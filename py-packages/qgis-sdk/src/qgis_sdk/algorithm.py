"""Processing algorithms: declarative parameters and outputs.

Now with extended param/output kinds and tags/help_url/flags support.

    from qgis_sdk import Algorithm, parameter, output

    class BufferAdvanced(Algorithm):
        id = "my_plugin:buffer_advanced"
        name = "Advanced Buffer"
        group = "Vector geometry"
        tags = ["buffer", "geometry"]
        help_url = "https://example.com/docs"

        input_layer = parameter.source("Input layer")
        distance = parameter.distance("Buffer distance", default=10.0)
        dissolve = parameter.boolean("Dissolve results", default=False)

        output_layer = output.sink("Buffered")

        def process(self, context):
            ...

The parameter model is plain Python — it can be inspected and tested without
QGIS. Only :meth:`Algorithm.to_qgis` touches ``processing``.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List

__all__ = ["Algorithm", "OutputSpec", "ParamSpec", "output", "parameter"]


@dataclass(frozen=True)
class ParamSpec:
    """One declared algorithm parameter."""

    kind: str
    description: str
    required: bool = True
    default: Any = None
    options: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    # Extended
    metadata: Dict[str, Any] | None = None
    advanced: bool = False
    default_expression: str | None = None

    def validate(self, value: Any) -> Any:
        """Check ``value`` against this spec and return it."""
        if value is None:
            if self.required and self.default is None:
                raise ValueError(f"{self.description!r} is required")
            return self.default
        if self.options and value not in self.options:
            raise ValueError(
                f"{self.description!r} must be one of {', '.join(self.options)}, got {value!r}"
            )
        if self.kind == "distance" and (
            (self.minimum is not None and value < self.minimum)
            or (self.maximum is not None and value > self.maximum)
        ):
            raise ValueError(f"{self.description!r} is out of range")
        return value


@dataclass(frozen=True)
class OutputSpec:
    """One declared algorithm output."""

    kind: str
    description: str


class parameter:
    """Namespace of parameter factories, mirroring QGIS parameter types."""

    @staticmethod
    def source(description: str, *, required: bool = True, advanced: bool = False) -> ParamSpec:
        return ParamSpec("source", description, required=required, advanced=advanced)

    @staticmethod
    def distance(
        description: str,
        *,
        default: float | None = None,
        minimum: float | None = 0.0,
        maximum: float | None = None,
        advanced: bool = False,
    ) -> ParamSpec:
        return ParamSpec(
            "distance", description, required=default is None, default=default,
            minimum=minimum, maximum=maximum, advanced=advanced,
        )

    @staticmethod
    def boolean(description: str, *, default: bool = False, advanced: bool = False) -> ParamSpec:
        return ParamSpec("boolean", description, required=False, default=default, advanced=advanced)

    @staticmethod
    def enum(
        description: str, options: list[str], *, default: str | None = None, advanced: bool = False
    ) -> ParamSpec:
        return ParamSpec(
            "enum", description, required=default is None, default=default,
            options=tuple(options), advanced=advanced,
        )

    @staticmethod
    def string(description: str, *, default: str | None = None, advanced: bool = False) -> ParamSpec:
        return ParamSpec("string", description, required=default is None, default=default, advanced=advanced)

    @staticmethod
    def number(
        description: str, *, default: float | None = None,
        minimum: float | None = None, maximum: float | None = None, advanced: bool = False,
    ) -> ParamSpec:
        return ParamSpec(
            "number", description, required=default is None, default=default,
            minimum=minimum, maximum=maximum, advanced=advanced,
        )

    @staticmethod
    def crs(description: str, *, default: str = "EPSG:4326", advanced: bool = False) -> ParamSpec:
        return ParamSpec("crs", description, required=False, default=default, advanced=advanced)

    # Extended types
    @staticmethod
    def layer(description: str, *, required: bool = True, advanced: bool = False) -> ParamSpec:
        return ParamSpec("layer", description, required=required, advanced=advanced)

    @staticmethod
    def vector(description: str, *, required: bool = True, advanced: bool = False) -> ParamSpec:
        return ParamSpec("vector", description, required=required, advanced=advanced)

    @staticmethod
    def raster(description: str, *, required: bool = True, advanced: bool = False) -> ParamSpec:
        return ParamSpec("raster", description, required=required, advanced=advanced)

    @staticmethod
    def field(description: str, *, parent: str = "", required: bool = True, advanced: bool = False) -> ParamSpec:
        return ParamSpec("field", description, required=required, advanced=advanced, metadata={"parent": parent})

    @staticmethod
    def multiple_layer(description: str, *, required: bool = True, advanced: bool = False) -> ParamSpec:
        return ParamSpec("multiple_layer", description, required=required, advanced=advanced)

    @staticmethod
    def expression(description: str, *, default: str = "", parent: str = "", advanced: bool = False) -> ParamSpec:
        return ParamSpec("expression", description, required=False, default=default, advanced=advanced, metadata={"parent": parent})

    @staticmethod
    def extent(description: str, *, required: bool = True, advanced: bool = False) -> ParamSpec:
        return ParamSpec("extent", description, required=required, advanced=advanced)

    @staticmethod
    def point(description: str, *, required: bool = True, advanced: bool = False) -> ParamSpec:
        return ParamSpec("point", description, required=required, advanced=advanced)

    @staticmethod
    def geometry(description: str, *, required: bool = True, advanced: bool = False) -> ParamSpec:
        return ParamSpec("geometry", description, required=required, advanced=advanced)

    @staticmethod
    def range(description: str, *, default: tuple = (0, 100), advanced: bool = False) -> ParamSpec:
        return ParamSpec("range", description, required=False, default=default, advanced=advanced)

    @staticmethod
    def matrix(description: str, *, default: list = None, advanced: bool = False) -> ParamSpec:
        return ParamSpec("matrix", description, required=False, default=default or [], advanced=advanced)

    @staticmethod
    def file(description: str, *, required: bool = True, extension: str = "", advanced: bool = False) -> ParamSpec:
        return ParamSpec("file", description, required=required, advanced=advanced, metadata={"extension": extension})

    @staticmethod
    def folder(description: str, *, required: bool = True, advanced: bool = False) -> ParamSpec:
        return ParamSpec("folder", description, required=required, advanced=advanced)

    @staticmethod
    def authcfg(description: str, *, required: bool = False, advanced: bool = False) -> ParamSpec:
        return ParamSpec("authcfg", description, required=required, advanced=advanced)

    @staticmethod
    def color(description: str, *, default: str = "#000000", advanced: bool = False) -> ParamSpec:
        return ParamSpec("color", description, required=False, default=default, advanced=advanced)

    @staticmethod
    def layout(description: str, *, required: bool = True, advanced: bool = False) -> ParamSpec:
        return ParamSpec("layout", description, required=required, advanced=advanced)

    @staticmethod
    def map_theme(description: str, *, required: bool = True, advanced: bool = False) -> ParamSpec:
        return ParamSpec("map_theme", description, required=required, advanced=advanced)

    @staticmethod
    def projection(description: str, *, default: str = "EPSG:4326", advanced: bool = False) -> ParamSpec:
        return ParamSpec("projection", description, required=False, default=default, advanced=advanced)


class output:
    """Namespace of output factories."""

    @staticmethod
    def sink(description: str) -> OutputSpec:
        return OutputSpec("sink", description)

    @staticmethod
    def layer(description: str) -> OutputSpec:
        return OutputSpec("layer", description)

    @staticmethod
    def file(description: str) -> OutputSpec:
        return OutputSpec("file", description)


class Algorithm:
    """Base class for a QGIS Processing algorithm."""

    id: ClassVar[str] = ""
    name: ClassVar[str] = ""
    group: ClassVar[str] = ""
    group_id: ClassVar[str] = ""
    description: ClassVar[str] = ""
    tags: ClassVar[List[str]] = []
    help_url: ClassVar[str] = ""
    flags: ClassVar[Dict[str, bool]] = {}
    provider_id: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.parameters: dict[str, ParamSpec] = {}
        cls.outputs: dict[str, OutputSpec] = {}
        for klass in reversed(cls.__mro__):
            for attribute, value in vars(klass).items():
                if isinstance(value, ParamSpec):
                    cls.parameters[attribute] = value
                elif isinstance(value, OutputSpec):
                    cls.outputs[attribute] = value

    # -- declaration ------------------------------------------------------

    @classmethod
    def declared_parameters(cls) -> Iterator[tuple[str, ParamSpec]]:
        yield from cls.parameters.items()

    @classmethod
    def declared_outputs(cls) -> Iterator[tuple[str, OutputSpec]]:
        yield from cls.outputs.items()

    @classmethod
    def defaults(cls) -> dict[str, Any]:
        """Every parameter that has a default, keyed by attribute name."""
        return {
            name: spec.default
            for name, spec in cls.parameters.items()
            if spec.default is not None
        }

    # -- execution --------------------------------------------------------

    def process(self, context: Any) -> dict[str, Any]:
        """Run the algorithm. Subclasses must override this."""
        raise NotImplementedError(f"{type(self).__name__} must implement process()")

    def run(self, context: Any) -> dict[str, Any]:
        """Validate the context against the declared parameters, then process."""
        for name, spec in self.parameters.items():
            spec.validate(context.get(name) if hasattr(context, "get") else None)
        return self.process(context)

    # -- QGIS bridge ------------------------------------------------------

    def to_qgis(self) -> Any:
        """Build the ``QgsProcessingAlgorithm`` this class describes."""
        from .processing_bridge import build_algorithm  # lazy: needs QGIS

        return build_algorithm(self)
