"""Tests for qgis_sdk.network — requests-like API + QGIS wrapper.

Uses project's own testing fixtures: fake_network_manager, fake_session,
fake_content_fetcher, fake_network_response, fake_iface, fake_action_factory.
"""

from __future__ import annotations

from pathlib import Path

import pytest



# ── Response ────────────────────────────────────────────────────────────────

def test_network_response(fake_network_response):
    # Uses fixture
    assert fake_network_response.ok
    assert fake_network_response.status_code == 200
    assert fake_network_response.text == '{"ok": true}'
    assert fake_network_response.json() == {"ok": True}
    assert fake_network_response.reason == "OK"
    assert not fake_network_response.is_redirect
    assert bool(fake_network_response) is True

    # iter_content
    chunks = list(fake_network_response.iter_content(chunk_size=5))
    assert b"".join(chunks) == fake_network_response.content

    # Custom response
    from qgis_sdk.testing import FakeNetworkResponse

    resp2 = FakeNetworkResponse(url="https://example.com", status_code=404, error="Not Found", reason="Not Found")
    assert not resp2.ok
    with pytest.raises(Exception):
        resp2.raise_for_status()

    # Real class
    from qgis_sdk.network import NetworkResponse

    resp = NetworkResponse(url="https://example.com", status_code=200, content=b'{"ok": true}')
    assert resp.ok
    assert resp.json() == {"ok": True}
    assert resp.text == '{"ok": true}'
    assert resp.reason == "OK"


def test_network_response_requests_like():
    from qgis_sdk.network import NetworkResponse

    resp = NetworkResponse(url="https://example.com", status_code=200, content=b'{"a": 1}', headers={"content-type": "application/json"})
    assert resp.ok
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json"
    assert resp.json()["a"] == 1
    assert list(resp.iter_content(2))
    assert resp.elapsed >= 0
    assert resp.url == "https://example.com"


# ── NetworkManager + Session (requests-like) ────────────────────────────────

def test_network_manager_fallback():
    from qgis_sdk.network import NetworkManager

    mgr = NetworkManager()
    assert hasattr(mgr, "get")
    assert hasattr(mgr, "post")
    assert hasattr(mgr, "put")
    assert hasattr(mgr, "patch")
    assert hasattr(mgr, "delete")
    assert hasattr(mgr, "head")
    assert hasattr(mgr, "request")
    assert hasattr(mgr, "download")
    assert hasattr(mgr, "fetch")
    assert hasattr(mgr, "fetch_blocking")
    assert hasattr(mgr, "session")

    mgr2 = NetworkManager.instance()
    assert mgr2 is not None
    mgr3 = NetworkManager.instance()
    assert mgr2 is mgr3


def test_requests_like_top_level_functions():
    from qgis_sdk.network import get, post, put, patch, delete, head, options, request, Session

    # These should be callable and not require QGIS
    assert callable(get)
    assert callable(post)
    assert callable(put)
    assert callable(patch)
    assert callable(delete)
    assert callable(head)
    assert callable(options)
    assert callable(request)
    assert callable(Session)


def test_session_requests_like(fake_session):
    # Uses fake_session fixture — requests-like Session
    assert hasattr(fake_session, "get")
    assert hasattr(fake_session, "post")
    assert hasattr(fake_session, "put")
    assert hasattr(fake_session, "patch")
    assert hasattr(fake_session, "delete")
    assert hasattr(fake_session, "head")
    assert hasattr(fake_session, "request")

    # Test params merging
    resp = fake_session.get("https://example.com/api", params={"q": "test", "page": 1})
    assert resp.ok
    assert len(fake_session.requests) == 1
    req = fake_session.requests[0]
    assert "q=test" in req["url"] or req["params"] == {"q": "test", "page": 1}
    assert req["method"] == "GET"

    # Test json data
    resp2 = fake_session.post("https://example.com/api", json={"key": "value"})
    assert resp2.ok
    assert fake_session.requests[1]["json"] == {"key": "value"}

    # Test headers merging
    fake_session.headers = {"User-Agent": "TestAgent"}
    resp3 = fake_session.get("https://example.com/api", headers={"X-Custom": "1"})
    assert "User-Agent" in fake_session.requests[2]["headers"]
    assert "X-Custom" in fake_session.requests[2]["headers"]

    # Test context manager
    with fake_session as s:
        r = s.get("https://example.com/api")
        assert r.ok


def test_fake_network_manager_requests_like(fake_network_manager):
    # Uses fixture fake_network_manager — requests-like
    from qgis_sdk.testing import FakeNetworkResponse

    # Setup canned responses
    fake_network_manager.responses = {
        "https://example.com/api": FakeNetworkResponse(url="https://example.com/api", content=b'{"data": 123}'),
        "https://example.com/search": FakeNetworkResponse(url="https://example.com/search", content=b'{"results": []}'),
    }

    # GET
    resp = fake_network_manager.get("https://example.com/api")
    assert resp.ok
    assert resp.json() == {"data": 123}
    assert len(fake_network_manager.requests) == 1
    assert fake_network_manager.requests[0]["url"] == "https://example.com/api"
    assert fake_network_manager.requests[0]["method"] == "GET"

    # GET with params — like requests
    resp2 = fake_network_manager.get("https://example.com/search", params={"q": "test"})
    assert resp2.ok
    assert "q=test" in fake_network_manager.requests[1]["url"]

    # POST with json — like requests
    resp3 = fake_network_manager.post("https://example.com/api", json={"key": "val"})
    assert resp3.ok
    assert fake_network_manager.requests[2]["json"] == {"key": "val"}
    assert fake_network_manager.requests[2]["method"] == "POST"

    # PUT, PATCH, DELETE, HEAD, OPTIONS
    fake_network_manager.put("https://example.com/api", json={"update": True})
    fake_network_manager.patch("https://example.com/api", json={"patch": True})
    fake_network_manager.delete("https://example.com/api")
    fake_network_manager.head("https://example.com/api")
    fake_network_manager.options("https://example.com/api")
    assert len(fake_network_manager.requests) == 8

    # Default mock for unknown URL
    resp_unknown = fake_network_manager.get("https://other.com")
    assert resp_unknown.ok
    assert resp_unknown.json()["mock"] is True

    # Download
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "file.json"
        fake_network_manager.download("https://example.com/api", dest, progress_callback=lambda p: None)
        assert dest.exists()
        assert len(fake_network_manager.downloads) == 1


def test_fetch_helpers_exist():
    from qgis_sdk.network import fetch, fetch_json, fetch_text, download

    assert callable(fetch)
    assert callable(fetch_json)
    assert callable(fetch_text)
    assert callable(download)


# ── ContentFetcher ──────────────────────────────────────────────────────────

def test_content_fetcher_fallback():
    from qgis_sdk.network import ContentFetcher

    fetcher = ContentFetcher()
    assert hasattr(fetcher, "fetch")
    assert hasattr(fetcher, "fetch_blocking")
    assert hasattr(fetcher, "content_as_string")
    assert hasattr(fetcher, "finished")


def test_fake_content_fetcher(fake_content_fetcher):
    # Uses fixture
    assert fake_content_fetcher.content_as_string() == '{"ok": true}'

    called = []
    fake_content_fetcher.finished.connect(lambda: called.append(True))
    fake_content_fetcher.fetch("https://example.com")
    assert len(called) >= 1

    # With params — requests-like
    fake_content_fetcher.fetch("https://example.com/api", params={"q": "test"})
    assert "q=test" in fake_content_fetcher.url or fake_content_fetcher.url == "https://example.com/api"


# ── NetworkAccessManager ────────────────────────────────────────────────────

def test_network_access_manager():
    from qgis_sdk.network import NetworkAccessManager

    http = NetworkAccessManager(timeout=5000)
    assert hasattr(http, "request")
    assert hasattr(http, "get")
    assert hasattr(http, "post")
    assert hasattr(http, "put")
    assert hasattr(http, "patch")
    assert hasattr(http, "delete")
    assert hasattr(http, "head")


# ── Integration with Plugin (using fixtures) ────────────────────────────────

def test_network_with_fake_iface_integration(fake_iface, fake_action_factory, fake_network_manager):
    """Plugin can use network manager with fake iface — uses fixtures."""
    from qgis_sdk import Plugin, action, toolbar
    from qgis_sdk.testing import FakeNetworkResponse

    # Setup canned response via fixture
    fake_network_manager.responses = {
        "https://api.example.com": FakeNetworkResponse(content=b'{"count": 5}')
    }

    class MyPlugin(Plugin):
        name = "test_network_plugin"
        version = "0.1.0"

        @toolbar("Test")
        @action(tooltip="Fetch data")
        def fetch_data(self, iface):
            # Use injected fake manager (in real plugin would use NetworkManager.instance())
            resp = fake_network_manager.get("https://api.example.com", params={"q": "test"})
            iface.messageBar().pushMessage(f"Fetched {resp.json()['count']} items")

    MyPlugin.action_factory = staticmethod(fake_action_factory)
    plugin = MyPlugin(fake_iface)
    plugin.init_gui()
    fake_iface.toolbar_icons[0].trigger()
    assert "Fetched 5 items" in fake_iface.messages[0]
    assert fake_network_manager.requests[0]["params"] == {"q": "test"}


def test_network_session_with_fake_iface(fake_iface, fake_action_factory, fake_session):
    """Plugin using Session — requests-like."""
    from qgis_sdk import Plugin, action, toolbar
    from qgis_sdk.testing import FakeNetworkResponse

    fake_session.responses = {
        "https://api.example.com/data": FakeNetworkResponse(content=b'{"count": 10}')
    }

    class MyPlugin(Plugin):
        name = "test_session_plugin"
        version = "0.1.0"

        @toolbar("Test")
        @action(tooltip="Fetch with session")
        def fetch_with_session(self, iface):
            with fake_session as session:
                resp = session.get("https://api.example.com/data", params={"limit": 10})
                resp.raise_for_status()
                iface.messageBar().pushMessage(f"Got {resp.json()['count']}")

    MyPlugin.action_factory = staticmethod(fake_action_factory)
    plugin = MyPlugin(fake_iface)
    plugin.init_gui()
    fake_iface.toolbar_icons[0].trigger()
    assert "Got 10" in fake_iface.messages[0]
