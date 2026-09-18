"""The declarative algorithm model, with no QGIS involved."""

from __future__ import annotations

import pytest

from qgis_sdk import Algorithm, output, parameter


class FakeContext:
    def __init__(self, values=None):
        self.values = values or {}
        self.progress = []

    def get(self, name, default=None):
        return self.values.get(name, default)

    def set_progress(self, fraction):
        self.progress.append(fraction)

    @property
    def is_canceled(self):
        return False


class Buffer(Algorithm):
    id = "sample:buffer"
    name = "Buffer"
    group = "Vector geometry"
    description = "Buffers features."

    input_layer = parameter.source("Input layer")
    distance = parameter.distance("Buffer distance", default=10.0)
    dissolve = parameter.boolean("Dissolve results", default=False)
    end_cap = parameter.enum("End cap style", ["Round", "Flat"], default="Round")

    output_layer = output.sink("Buffered")

    def process(self, context):
        context.set_progress(1.0)
        return {
            "distance": context.get("distance"),
            "dissolve": context.get("dissolve"),
            "end_cap": context.get("end_cap"),
        }


def test_parameters_are_collected():
    assert list(Buffer.parameters) == ["input_layer", "distance", "dissolve", "end_cap"]


def test_outputs_are_collected():
    assert list(Buffer.outputs) == ["output_layer"]
    assert Buffer.outputs["output_layer"].kind == "sink"


def test_defaults_are_reported():
    assert Buffer.defaults() == {"distance": 10.0, "dissolve": False, "end_cap": "Round"}


def test_enum_spec_keeps_options_in_order():
    assert Buffer.parameters["end_cap"].options == ("Round", "Flat")


def test_required_parameter_without_value_fails():
    with pytest.raises(ValueError, match="required"):
        Buffer.parameters["input_layer"].validate(None)


def test_enum_value_is_checked():
    with pytest.raises(ValueError, match="must be one of"):
        Buffer.parameters["end_cap"].validate("Triangle")


def test_distance_range_is_checked():
    with pytest.raises(ValueError, match="out of range"):
        Buffer.parameters["distance"].validate(-5.0)


def test_run_passes_the_context_through():
    context = FakeContext({"input_layer": "memory:points", "distance": 25.0})
    result = Buffer().run(context)

    assert result == {"distance": 25.0, "dissolve": None, "end_cap": None}
    assert context.progress == [1.0]


def test_run_rejects_a_missing_required_parameter():
    with pytest.raises(ValueError, match="required"):
        Buffer().run(FakeContext({"distance": 25.0}))


def test_base_algorithm_process_is_abstract():
    class Empty(Algorithm):
        id = "sample:empty"

    with pytest.raises(NotImplementedError):
        Empty().process(FakeContext())


def test_subclasses_do_not_share_parameter_state():
    class Other(Algorithm):
        id = "sample:other"
        width = parameter.number("Width", default=1.0)

    assert list(Other.parameters) == ["width"]
    assert "input_layer" not in Other.parameters


def test_inherited_parameters_are_kept():
    class Wider(Buffer):
        segments = parameter.number("Segments", default=8)

    assert list(Wider.parameters) == [
        "input_layer",
        "distance",
        "dissolve",
        "end_cap",
        "segments",
    ]
