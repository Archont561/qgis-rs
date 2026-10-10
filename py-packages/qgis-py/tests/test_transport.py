"""Response-version guards through the public raw-invoke boundary.

Only the compiled extension's JSON answer is scripted. The Python client's
request encoding, version check and exception construction are real.
"""

from __future__ import annotations

import json

import pytest

import qgis_py
from qgis_py import _transport


@pytest.mark.parametrize("received", [0, 2, None], ids=["older", "newer", "missing"])
@pytest.mark.parametrize("ok", [True, False], ids=["success", "failure"])
def test_an_incompatible_response_is_rejected_before_its_result(monkeypatch, received, ok):
    response = {
        "ok": ok,
        "result": {"kind": "invalid_extent", "error": "Do not interpret this result"},
    }
    if received is not None:
        response["transport_version"] = received
    requests = []

    def native_invoke(request_json):
        requests.append(json.loads(request_json))
        return json.dumps(response)

    monkeypatch.setattr(_transport._core, "invoke", native_invoke)

    with pytest.raises(qgis_py.TransportMismatch) as caught:
        qgis_py.invoke("ping", {"value": [1, "two"]})

    assert isinstance(caught.value, qgis_py.EngineError)
    assert isinstance(caught.value, RuntimeError)
    assert caught.value.kind == "unsupported_transport"
    assert caught.value.detail == {
        "supported": qgis_py.TRANSPORT_VERSION,
        "received": received,
    }
    assert requests == [
        {
            "transport_version": qgis_py.TRANSPORT_VERSION,
            "operation": "ping",
            "payload": {"value": [1, "two"]},
        }
    ]
