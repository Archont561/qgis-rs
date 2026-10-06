"""The scripted network transport: what it answers, and what it refuses to.

Pure Python, no sockets, no sleeping. The behaviour worth pinning is as much
about the refusals as the replies — an unscripted URL raises instead of
inventing a 200, and a sequence that runs out raises instead of repeating,
because both of those silences are how a network test passes while testing
nothing.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qgis_sdk.testing import (
    FakeNetworkTransport,
    FakeResponse,
    NoScriptedReply,
    RedirectLoop,
)


@pytest.fixture
def transport() -> FakeNetworkTransport:
    return FakeNetworkTransport()


def test_a_scripted_reply_comes_back_decoded(transport: FakeNetworkTransport) -> None:
    transport.reply("GET", "https://example.test/layers", json_data={"layers": ["roads"]})

    response = transport.get("https://example.test/layers")

    assert response.ok
    assert response.json() == {"layers": ["roads"]}
    assert response.headers["content-type"] == "application/json"


def test_an_unscripted_route_is_a_failed_expectation(transport: FakeNetworkTransport) -> None:
    """No default answer — the whole difference from the old FakeNetworkManager."""
    transport.reply("GET", "https://example.test/layers", json_data={})

    with pytest.raises(NoScriptedReply) as refusal:
        transport.get("https://example.test/other")

    assert "GET https://example.test/other" in str(refusal.value)
    assert "https://example.test/layers" in str(refusal.value), "it names what *is* scripted"


def test_a_sequence_is_consumed_in_order_and_then_runs_out(
    transport: FakeNetworkTransport,
) -> None:
    """A retry policy is only testable if the second answer can differ."""
    transport.reply_sequence(
        "GET",
        "https://example.test/flaky",
        [
            FakeResponse(status_code=503, content=b"try later"),
            FakeResponse(status_code=200, json_data={"ok": True}),
        ],
    )

    assert transport.get("https://example.test/flaky").status_code == 503
    assert transport.get("https://example.test/flaky").json() == {"ok": True}
    with pytest.raises(NoScriptedReply, match="scripted with 2 replies"):
        transport.get("https://example.test/flaky")


def test_a_sequence_can_be_asked_to_hold_its_last_answer(
    transport: FakeNetworkTransport,
) -> None:
    transport.reply_sequence(
        "GET",
        "https://example.test/eventually",
        [FakeResponse(status_code=500), FakeResponse(status_code=200)],
        repeat_last=True,
    )

    codes = [transport.get("https://example.test/eventually").status_code for _ in range(4)]
    assert codes == [500, 200, 200, 200]


def test_a_failure_is_a_response_that_raises_for_status(
    transport: FakeNetworkTransport,
) -> None:
    transport.fail("GET", "https://example.test/down", error="connection refused")

    response = transport.get("https://example.test/down")

    assert not response.ok
    assert response.error == "connection refused"
    with pytest.raises(Exception, match="connection refused"):
        response.raise_for_status()


def test_a_failure_can_raise_instead_of_answering(transport: FakeNetworkTransport) -> None:
    """Some clients see an exception, not a response; both are scriptable."""
    transport.fail("GET", "https://example.test/down", raises=TimeoutError("timed out"))

    with pytest.raises(TimeoutError, match="timed out"):
        transport.get("https://example.test/down")


def test_a_delay_advances_a_virtual_clock_and_nothing_else(
    transport: FakeNetworkTransport,
) -> None:
    """Determinism rule from doc-5: no test sleeps to wait for a fake."""
    transport.reply("GET", "https://example.test/slow", json_data={})
    transport.delay("GET", "https://example.test/slow", 2.5)

    response = transport.get("https://example.test/slow")

    assert transport.clock == 2.5
    assert response.elapsed == 2.5


def test_a_redirect_is_followed_and_kept_in_the_history(
    transport: FakeNetworkTransport,
) -> None:
    transport.redirect("GET", "https://example.test/old", to="https://example.test/new")
    transport.reply("GET", "https://example.test/new", json_data={"moved": True})

    response = transport.get("https://example.test/old")

    assert response.url == "https://example.test/new"
    assert response.json() == {"moved": True}
    assert [hop.status_code for hop in response.history] == [302]


def test_a_caller_can_refuse_to_follow_a_redirect(transport: FakeNetworkTransport) -> None:
    transport.redirect("GET", "https://example.test/old", to="https://example.test/new", status_code=301)

    response = transport.get("https://example.test/old", allow_redirects=False)

    assert response.status_code == 301
    assert response.headers["location"] == "https://example.test/new"
    assert response.is_redirect


def test_a_redirect_loop_is_caught_rather_than_hung(transport: FakeNetworkTransport) -> None:
    transport.redirect("GET", "https://example.test/a", to="https://example.test/b")
    transport.redirect("GET", "https://example.test/b", to="https://example.test/a")

    with pytest.raises(RedirectLoop):
        transport.get("https://example.test/a")


def test_history_records_the_url_the_caller_really_asked_for(
    transport: FakeNetworkTransport,
) -> None:
    transport.reply("*", "https://example.test/search?q=roads", json_data={"hits": 1})

    transport.get("https://example.test/search", params={"q": "roads"})

    assert transport.requests[0]["url"] == "https://example.test/search?q=roads"
    assert transport.requests[0]["original_url"] == "https://example.test/search"
    assert transport.calls.assert_called_once("network", "get").args["params"] == {"q": "roads"}


def test_a_wildcard_route_answers_any_verb(transport: FakeNetworkTransport) -> None:
    transport.reply("*", "https://example.test/any", json_data={"verb": "any"})

    for call in (transport.get, transport.post, transport.delete):
        assert call("https://example.test/any").json() == {"verb": "any"}


def test_reset_forgets_the_script_the_history_and_the_clock(
    transport: FakeNetworkTransport,
) -> None:
    transport.reply("GET", "https://example.test/x", json_data={})
    transport.delay("GET", "https://example.test/x", 1.0)
    transport.get("https://example.test/x")

    transport.reset()

    assert transport.requests == []
    assert transport.clock == 0.0
    assert len(transport.calls) == 0
    with pytest.raises(NoScriptedReply):
        transport.get("https://example.test/x")


@settings(max_examples=50, deadline=None)
@given(
    bodies=st.lists(st.text(max_size=40), min_size=1, max_size=5),
    chunk_size=st.integers(min_value=1, max_value=16),
)
def test_chunks_reconstruct_the_body_whatever_the_chunk_size(
    bodies: list[str], chunk_size: int
) -> None:
    """doc-5's property list: "network chunks reconstruct the original content"."""
    transport = FakeNetworkTransport()
    for index, body in enumerate(bodies):
        transport.reply(
            "GET", f"https://example.test/{index}", content=body.encode("utf-8")
        )

    for index, body in enumerate(bodies):
        response = transport.get(f"https://example.test/{index}")
        rebuilt = b"".join(response.iter_content(chunk_size=chunk_size))
        assert rebuilt == body.encode("utf-8")


@settings(max_examples=50, deadline=None)
@given(
    delays=st.lists(st.floats(min_value=0, max_value=30, allow_nan=False), min_size=1, max_size=6)
)
def test_the_virtual_clock_is_the_sum_of_the_delays_served(delays: list[float]) -> None:
    transport = FakeNetworkTransport()
    for index, seconds in enumerate(delays):
        url = f"https://example.test/{index}"
        transport.reply("GET", url, json_data={})
        transport.delay("GET", url, seconds)

    for index in range(len(delays)):
        transport.get(f"https://example.test/{index}")

    assert transport.clock == pytest.approx(sum(delays))
