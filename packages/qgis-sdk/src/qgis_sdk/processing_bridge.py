"""Bridge from the declarative parameter model to QGIS Processing.

Everything here touches ``processing``/``qgis.core`` and is therefore imported
lazily, from :meth:`qgis_sdk.Algorithm.to_qgis`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .algorithm import Algorithm, ParamSpec

__all__ = ["build_algorithm", "parameter_definition"]

#: Declarative kind -> the ``QgsProcessingParameterDefinition`` subclass name.
_PARAMETER_TYPES = {
    "source": "QgsProcessingParameterFeatureSource",
    "distance": "QgsProcessingParameterDistance",
    "boolean": "QgsProcessingParameterBoolean",
    "enum": "QgsProcessingParameterEnum",
    "string": "QgsProcessingParameterString",
    "number": "QgsProcessingParameterNumber",
    "crs": "QgsProcessingParameterCrs",
}

_OUTPUT_TYPES = {
    "sink": "QgsProcessingOutputVectorLayer",
    "layer": "QgsProcessingOutputVectorLayer",
    "file": "QgsProcessingOutputFile",
}


def parameter_definition(name: str, spec: ParamSpec, core: Any) -> Any:
    """Instantiate the QGIS parameter definition matching ``spec``."""
    class_name = _PARAMETER_TYPES.get(spec.kind)
    if class_name is None:
        raise ValueError(f"unknown parameter kind: {spec.kind!r}")
    definition = getattr(core, class_name)

    if spec.kind == "enum":
        return definition(name, spec.description, options=list(spec.options), optional=not spec.required, defaultValue=spec.default)
    if spec.kind == "distance":
        return definition(name, spec.description, parentParameterName="", optional=not spec.required, defaultValue=spec.default)
    if spec.kind in {"number", "string", "crs", "boolean"}:
        return definition(name, spec.description, optional=not spec.required, defaultValue=spec.default)
    return definition(name, spec.description, optional=not spec.required)


def build_algorithm(algorithm: Algorithm) -> Any:
    """Return a ``QgsProcessingAlgorithm`` instance for ``algorithm``."""
    from .runtime import qgis_core  # lazy: needs QGIS

    core = qgis_core()

    class Generated(core.QgsProcessingAlgorithm):  # type: ignore[name-defined]
        def name(self) -> str:
            return algorithm.id.split(":", 1)[-1] or algorithm.id

        def displayName(self) -> str:  # noqa: N802 - QGIS naming
            return algorithm.name

        def group(self) -> str:
            return algorithm.group

        def groupId(self) -> str:  # noqa: N802 - QGIS naming
            return algorithm.group.lower().replace(" ", "")

        def shortHelpString(self) -> str:  # noqa: N802 - QGIS naming
            return algorithm.description

        def createInstance(self):  # noqa: N802 - QGIS naming
            return Generated()

        def initAlgorithm(self, configuration=None):  # noqa: N802 - QGIS naming
            for param_name, spec in algorithm.declared_parameters():
                self.addParameter(parameter_definition(param_name, spec, core))
            for out_name, out_spec in algorithm.declared_outputs():
                self.addOutput(
                    getattr(core, _OUTPUT_TYPES[out_spec.kind])(out_name, out_spec.description)
                )

        def processAlgorithm(self, parameters, context, feedback):  # noqa: N802 - QGIS naming
            return algorithm.run(_ContextAdapter(parameters, context, feedback)) or {}

    return Generated()


class _ContextAdapter:
    """Present QGIS's ``parameters``/``context``/``feedback`` as one object."""

    def __init__(self, parameters: Any, context: Any, feedback: Any) -> None:
        self._parameters = parameters
        self.context = context
        self.feedback = feedback

    def get(self, name: str, default: Any = None) -> Any:
        return self._parameters.get(name, default)

    @property
    def is_canceled(self) -> bool:
        return bool(self.feedback is not None and self.feedback.isCanceled())

    def set_progress(self, fraction: float) -> None:
        if self.feedback is not None:
            self.feedback.setProgress(int(max(0.0, min(1.0, fraction)) * 100))
