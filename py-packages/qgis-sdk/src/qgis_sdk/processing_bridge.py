"""Bridge from the declarative parameter model to QGIS Processing.

Everything here touches ``processing``/``qgis.core`` and is therefore imported
lazily, from :meth:`qgis_sdk.Algorithm.to_qgis`.

Now includes provider registration (fix for hasProcessingProvider=True without provider).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, List

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .algorithm import Algorithm, ParamSpec

__all__ = ["build_algorithm", "build_provider", "parameter_definition", "register_provider", "unregister_provider"]

#: Declarative kind -> the ``QgsProcessingParameterDefinition`` subclass name.
_PARAMETER_TYPES = {
    "source": "QgsProcessingParameterFeatureSource",
    "distance": "QgsProcessingParameterDistance",
    "boolean": "QgsProcessingParameterBoolean",
    "enum": "QgsProcessingParameterEnum",
    "string": "QgsProcessingParameterString",
    "number": "QgsProcessingParameterNumber",
    "crs": "QgsProcessingParameterCrs",
    # Extended types
    "layer": "QgsProcessingParameterMapLayer",
    "vector": "QgsProcessingParameterVectorLayer",
    "raster": "QgsProcessingParameterRasterLayer",
    "field": "QgsProcessingParameterField",
    "multiple_layer": "QgsProcessingParameterMultipleLayers",
    "expression": "QgsProcessingParameterExpression",
    "extent": "QgsProcessingParameterExtent",
    "point": "QgsProcessingParameterPoint",
    "geometry": "QgsProcessingParameterGeometry",
    "range": "QgsProcessingParameterRange",
    "matrix": "QgsProcessingParameterMatrix",
    "file": "QgsProcessingParameterFile",
    "folder": "QgsProcessingParameterFolderDestination",
    "authcfg": "QgsProcessingParameterAuthConfig",
    "color": "QgsProcessingParameterColor",
    "layout": "QgsProcessingParameterLayout",
    "map_theme": "QgsProcessingParameterMapTheme",
    "projection": "QgsProcessingParameterCrs",
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
            return algorithm.name or algorithm.id

        def group(self) -> str:
            return getattr(algorithm, "group", "") or ""

        def groupId(self) -> str:  # noqa: N802 - QGIS naming
            gid = getattr(algorithm, "group_id", None) or getattr(algorithm, "group", "")
            return gid.lower().replace(" ", "") if gid else ""

        def shortHelpString(self) -> str:  # noqa: N802 - QGIS naming
            return getattr(algorithm, "description", "") or ""

        def shortDescription(self) -> str:  # noqa: N802
            return getattr(algorithm, "description", "") or ""

        def helpUrl(self) -> str:  # noqa: N802
            return getattr(algorithm, "help_url", "") or ""

        def tags(self):  # noqa: N802
            return getattr(algorithm, "tags", []) or []

        def flags(self):  # noqa: N802
            core_flags = 0
            # Map our flags to QGIS flags if available
            alg_flags = getattr(algorithm, "flags", {})
            if isinstance(alg_flags, dict):
                if alg_flags.get("no_threading"):
                    try:
                        core_flags |= core.QgsProcessingAlgorithm.FlagNoThreading
                    except AttributeError:
                        pass
                if alg_flags.get("not_batch"):
                    try:
                        core_flags |= core.QgsProcessingAlgorithm.FlagNotAvailableInBatch
                    except AttributeError:
                        pass
            return core_flags

        def createInstance(self):  # noqa: N802 - QGIS naming
            return Generated()

        def initAlgorithm(self, configuration=None):  # noqa: N802 - QGIS naming
            for param_name, spec in algorithm.declared_parameters():
                self.addParameter(parameter_definition(param_name, spec, core))
            for out_name, out_spec in algorithm.declared_outputs():
                self.addOutput(
                    getattr(core, _OUTPUT_TYPES.get(out_spec.kind, "QgsProcessingOutputVectorLayer"))(out_name, out_spec.description)
                )

        def processAlgorithm(self, parameters, context, feedback):  # noqa: N802 - QGIS naming
            # Wrap with progress and cancellation support
            try:
                adapter = _ContextAdapter(parameters, context, feedback)
                # Auto progress 0%
                if feedback:
                    try:
                        feedback.setProgress(0)
                    except Exception:
                        pass
                result = algorithm.run(adapter) or {}
                if feedback:
                    try:
                        feedback.setProgress(100)
                    except Exception:
                        pass
                return result
            except ValueError as e:
                # Convert bare ValueError to QgsProcessingException for QGIS UX
                try:
                    raise core.QgsProcessingException(str(e))
                except AttributeError:
                    raise
            except Exception as e:
                # Check cancellation
                if feedback and hasattr(feedback, "isCanceled") and feedback.isCanceled():
                    return {}
                raise

    return Generated()


def build_provider(algorithms: Iterable[Any], provider_id: str = "", provider_name: str = "", icon_path: str = "") -> Any:
    """Build a QgsProcessingProvider containing the given algorithms.

    Args:
        algorithms: iterable of Algorithm instances or classes
        provider_id: provider id, e.g. "my_plugin" — defaults to first algorithm's prefix
        provider_name: human name — defaults to provider_id
        icon_path: optional icon path
    """
    from .runtime import qgis_core

    core = qgis_core()

    # Normalize algorithms to instances
    algs: List[Any] = []
    for alg in algorithms:
        if isinstance(alg, type):
            try:
                algs.append(alg())
            except Exception:
                algs.append(alg)
        else:
            algs.append(alg)

    if not provider_id and algs:
        first = algs[0]
        alg_id = getattr(first, "id", "")
        if ":" in alg_id:
            provider_id = alg_id.split(":", 1)[0]
        else:
            provider_id = "qgis_sdk"

    provider_id = provider_id or "qgis_sdk"
    provider_name = provider_name or provider_id

    # Capture for closure
    _algs = algs
    _provider_id = provider_id
    _provider_name = provider_name
    _icon_path = icon_path

    class GeneratedProvider(core.QgsProcessingProvider):  # type: ignore[name-defined]
        def id(self) -> str:
            return _provider_id

        def name(self) -> str:
            return _provider_name

        def icon(self):
            if _icon_path:
                try:
                    # Try QgsApplication.getThemeIcon or QIcon
                    from qgis.PyQt.QtGui import QIcon  # type: ignore
                    import os
                    if os.path.exists(_icon_path):
                        return QIcon(_icon_path)
                except Exception:
                    pass
            try:
                return core.QgsProcessingProvider.icon(self)
            except Exception:
                # Fallback via _qt
                try:
                    from ._qt import QIcon
                    return QIcon()
                except Exception:
                    return None

        def loadAlgorithms(self):  # noqa: N802
            for alg in _algs:
                try:
                    if hasattr(alg, "to_qgis"):
                        qgis_alg = alg.to_qgis()
                    else:
                        qgis_alg = build_algorithm(alg)
                    self.addAlgorithm(qgis_alg)
                except Exception as e:
                    print(f"[Provider] failed to load algorithm {getattr(alg, 'id', alg)}: {e}")

    return GeneratedProvider()


def register_provider(provider: Any) -> bool:
    """Register provider with QgsApplication.processingRegistry()."""
    try:
        from qgis.core import QgsApplication  # type: ignore
        registry = QgsApplication.processingRegistry()
        if registry:
            # Check if already registered
            existing = registry.providerById(provider.id())
            if existing:
                registry.removeProvider(existing)
            registry.addProvider(provider)
            return True
    except Exception as e:
        print(f"[Provider] register failed: {e}")
    return False


def unregister_provider(provider: Any) -> bool:
    """Unregister provider."""
    try:
        from qgis.core import QgsApplication  # type: ignore
        registry = QgsApplication.processingRegistry()
        if registry:
            registry.removeProvider(provider)
            return True
    except Exception as e:
        print(f"[Provider] unregister failed: {e}")
    return False


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
