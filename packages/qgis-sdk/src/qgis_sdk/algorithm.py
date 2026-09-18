"""Processing algorithms: declarative parameters and outputs.

    from qgis_sdk import Algorithm, parameter, output

    class BufferAdvanced(Algorithm):
        id = "my_plugin:buffer_advanced"
        name = "Advanced Buffer"
        group = "Vector geometry"

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
from dataclasses import dataclass, field
from typing import Any, ClassVar

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
    def source(description: str, *, required: bool = True) -> ParamSpec:
        return ParamSpec("source", description, required=required)

    @staticmethod
    def distance(
        description: str,
        *,
        default: float | None = None,
        minimum: float | None = 0.0,
        maximum: float | None = None,
    ) -> ParamSpec:
        return ParamSpec(
            "distance", description, required=default is None, default=default,
            minimum=minimum, maximum=maximum,
        )

    @staticmethod
    def boolean(description: str, *, default: bool = False) -> ParamSpec:
        return ParamSpec("boolean", description, required=False, default=default)

    @staticmethod
    def enum(
        description: str, options: list[str], *, default: str | None = None
    ) -> ParamSpec:
        return ParamSpec(
            "enum", description, required=default is None, default=default,
            options=tuple(options),
        )

    @staticmethod
    def string(description: str, *, default: str | None = None) -> ParamSpec:
        return ParamSpec("string", description, required=default is None, default=default)

    @staticmethod
    def number(
        description: str, *, default: float | None = None,
        minimum: float | None = None, maximum: float | None = None,
    ) -> ParamSpec:
        return ParamSpec(
            "number", description, required=default is None, default=default,
            minimum=minimum, maximum=maximum,
        )

    @staticmethod
    def crs(description: str, *, default: str = "EPSG:4326") -> ParamSpec:
        return ParamSpec("crs", description, required=False, default=default)


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
    description: ClassVar[str] = ""

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
        """Build the ``QgsProcessingAlgorithm`` this class describes.

        Imported lazily: this is the only place the SDK needs Processing.
        """
        from .processing_bridge import build_algorithm  # lazy: needs QGIS

        return build_algorithm(self)
