"""A tiny plugin fixture used by the QGIS-hosted integration test."""

from qgis_sdk import Algorithm, action, algorithm, output, parameter, plugin, toolbar


@algorithm(id="fixture:echo", name="Echo", group="Integration")
class EchoAlgorithm(Algorithm):
    value = parameter.number("Value", default=0)
    result = output.file("Result")

    def process(self, context):
        destination = context.get("result")
        if destination:
            with open(destination, "w", encoding="utf-8") as stream:
                stream.write(str(context.get("value")))
        return {"result": destination or str(context.get("value"))}


@plugin(
    name="Simple fixture plugin",
    version="0.1.0",
    algorithms=[EchoAlgorithm],
)
class SimplePlugin:
    """Small declarative plugin with one action and one Processing algorithm."""

    def __init__(self, iface=None):
        self.iface = iface
        self.calls = 0

    @toolbar("Fixture tools")
    @action(tooltip="Run fixture action")
    def run(self, iface):
        self.calls += 1
        iface.messages.append("fixture action called")
