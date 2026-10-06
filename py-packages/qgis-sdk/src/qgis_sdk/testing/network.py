"""Network fakes: a scripted transport, plus the requests-like managers.

Two layers, deliberately separate.

:class:`FakeNetworkTransport` is the one doc-5 asks for: a script of replies
keyed by ``(method, url)``, with failures, virtual delays, redirects and reply
sequences, a request history, and **no default answer** — an unscripted URL
raises :class:`NoScriptedReply` rather than inventing a 200. A test that
matters says in its own body what the far side returns.

:class:`FakeNetworkManager` and friends are the older requests-like fakes that
plugin tests already use (``fake_network_manager``, ``fake_session``). They
keep their permissive default — an unscripted URL answers ``{"mock": true}`` —
because changing it would break existing suites, which AC#1 forbids. New
tests should prefer the transport.

Nothing here opens a socket; the only clock is a counter of virtual seconds,
so a "slow" response costs nothing and a test never sleeps.
"""

from __future__ import annotations

import json as json_module
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .calls import CallLog, call_log


def _build_url(url: str, params: Optional[Dict[str, Any]] = None) -> str:
    if not params:
        return url
    parsed = urlparse(url)
    existing = parse_qs(parsed.query)
    merged: Dict[str, Any] = {}
    for k, v in existing.items():
        merged[k] = v[0] if len(v) == 1 else v
    merged.update(params)
    query = urlencode(merged, doseq=True)
    return urlunparse(parsed._replace(query=query))


class FakeNetworkResponse:
    """Fake NetworkResponse — requests-like for testing without QGIS."""

    def __init__(
        self,
        url="https://example.com",
        status_code=200,
        content=b'{"ok": true}',
        headers=None,
        error=None,
        encoding="utf-8",
        elapsed=0.01,
        reason=None,
        cookies=None,
        json_data=None,
    ):
        if json_data is not None:
            content = json_module.dumps(json_data).encode("utf-8")
            headers = {"content-type": "application/json", **(headers or {})}
        self.url = url
        self.status_code = status_code
        self.content = content if isinstance(content, bytes) else str(content).encode("utf-8")
        self.headers = {k.lower(): v for k, v in (headers or {"content-type": "application/json"}).items()}
        self.error = error
        self.error_code = 0 if error is None else 1
        self.encoding = encoding
        self.elapsed = elapsed
        self.reason = reason or ("OK" if status_code == 200 else "Error")
        self.cookies = cookies or {}
        self.history: List["FakeNetworkResponse"] = []

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 400

    @property
    def text(self) -> str:
        try:
            return self.content.decode(self.encoding or "utf-8")
        except Exception:
            return self.content.decode("latin-1", errors="ignore")

    @property
    def apparent_encoding(self) -> str:
        return "utf-8"

    def json(self):
        return json_module.loads(self.text)

    def raise_for_status(self):
        if not self.ok:
            try:
                from ..network import HTTPError

                raise HTTPError(
                    f"{self.status_code} {self.reason}: {self.error or self.text[:200]} for url: {self.url}",
                    response=self,
                )
            except ImportError:
                raise Exception(f"HTTP {self.status_code}: {self.error or self.text[:200]}")

    def iter_content(self, chunk_size: int = 1024) -> Iterator[bytes]:
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i : i + chunk_size]

    def iter_lines(self, chunk_size: int = 1024, decode_unicode: bool = False) -> Iterator[Any]:
        lines = self.content.split(b"\n")
        for line in lines:
            if decode_unicode:
                yield line.decode(self.encoding or "utf-8", errors="ignore")
            else:
                yield line

    @property
    def is_redirect(self) -> bool:
        return self.status_code in (301, 302, 303, 307, 308)

    def __bool__(self):
        return self.ok

    def __repr__(self):
        return f"<FakeNetworkResponse [{self.status_code}]>"


#: doc-5 spells the scripted response ``FakeResponse``; it is the same class,
#: and ``FakeResponse(status_code=200, json_data={...})`` is the short form.
FakeResponse = FakeNetworkResponse


class NoScriptedReply(AssertionError):
    """Raised when the transport is asked for a route nobody scripted.

    An ``AssertionError`` on purpose: in a test this reads as a failed
    expectation, which is what an unscripted request is.
    """


class RedirectLoop(AssertionError):
    """Raised when scripted redirects never reach a terminal response."""


class _Route:
    """One scripted answer, or a sequence of them, for one method and URL."""

    def __init__(self) -> None:
        self.responses: List[FakeNetworkResponse] = []
        self.repeat_last: bool = True
        self.raises: Optional[BaseException] = None
        self.redirect_to: Optional[str] = None
        self.redirect_status: int = 302
        self.delay: float = 0.0
        self.served: int = 0

    def next_response(self, url: str) -> FakeNetworkResponse:
        if not self.responses:
            raise NoScriptedReply(f"no response scripted for {url}")
        index = self.served
        self.served += 1
        if index < len(self.responses):
            return self.responses[index]
        if self.repeat_last:
            return self.responses[-1]
        raise NoScriptedReply(
            f"{url} was scripted with {len(self.responses)} replies and asked "
            f"{self.served} times"
        )


class FakeNetworkTransport:
    """A scripted HTTP transport: no sockets, no sleeping, no default answer.

    ::

        transport = FakeNetworkTransport()
        transport.reply("GET", "https://example.test/layers", json_data={"layers": []})
        response = transport.get("https://example.test/layers")

    Scripting verbs — ``reply``, ``reply_sequence``, ``fail``, ``delay``,
    ``redirect`` — all key on ``(method, url)``; ``method="*"`` matches any
    verb. Requests land in :attr:`requests` and in the shared
    :class:`~qgis_sdk.testing.calls.CallLog` as ``network.<verb>`` calls.
    """

    max_redirects = 5

    def __init__(self, calls: Optional[CallLog] = None, headers: Optional[Dict[str, str]] = None):
        self.calls = call_log(calls)
        self.headers: Dict[str, str] = dict(headers or {})
        self.requests: List[Dict[str, Any]] = []
        #: Virtual seconds accrued by scripted delays. Nothing ever sleeps.
        self.clock: float = 0.0
        self._routes: Dict[Tuple[str, str], _Route] = {}

    # ── scripting ───────────────────────────────────────────────────────────

    def reply(
        self,
        method: str,
        url: str,
        response: Optional[FakeNetworkResponse] = None,
        **kwargs: Any,
    ) -> FakeNetworkResponse:
        """Script one response, reused for every request to this route."""
        answer = response if response is not None else FakeResponse(url=url, **kwargs)
        route = self._route(method, url)
        route.responses = [answer]
        route.repeat_last = True
        route.served = 0
        return answer

    def reply_sequence(
        self, method: str, url: str, responses: List[FakeNetworkResponse], repeat_last: bool = False
    ) -> None:
        """Script responses consumed in order — a retry test's whole point.

        With ``repeat_last=False`` (the default) a request past the end of the
        sequence raises :class:`NoScriptedReply`: a caller that retried more
        often than the test scripted is a finding, not a pass.
        """
        route = self._route(method, url)
        route.responses = list(responses)
        route.repeat_last = repeat_last
        route.served = 0

    def fail(
        self,
        method: str,
        url: str,
        error: str = "connection refused",
        status_code: int = 0,
        raises: Optional[BaseException] = None,
    ) -> None:
        """Script a failure: an error response, or an exception to raise."""
        route = self._route(method, url)
        if raises is not None:
            route.raises = raises
            return
        route.responses = [
            FakeResponse(url=url, status_code=status_code, error=error, content=b"", reason="Error")
        ]
        route.repeat_last = True
        route.served = 0

    def delay(self, method: str, url: str, seconds: float) -> None:
        """Attach a virtual delay to a route — advances :attr:`clock` only."""
        self._route(method, url).delay = seconds

    def redirect(self, method: str, url: str, to: str, status_code: int = 302) -> None:
        """Script a redirect; the transport follows it and keeps the history."""
        route = self._route(method, url)
        route.redirect_to = to
        route.redirect_status = status_code

    def reset(self) -> None:
        """Forget the script, the history, the calls and the virtual clock."""
        self._routes.clear()
        self.requests.clear()
        self.calls.reset()
        self.clock = 0.0

    # ── requesting ──────────────────────────────────────────────────────────

    def request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        allow_redirects: bool = True,
        **kwargs: Any,
    ) -> FakeNetworkResponse:
        """Answer one request from the script, or raise :class:`NoScriptedReply`."""
        verb = method.upper()
        full_url = _build_url(url, params)
        merged_headers = {**self.headers, **(headers or {})}
        self.requests.append(
            {
                "method": verb,
                "url": full_url,
                "original_url": url,
                "params": params,
                "headers": merged_headers,
                **kwargs,
            }
        )
        self.calls.record("network", verb.lower(), url=full_url, params=params, **kwargs)
        return self._serve(verb, full_url, allow_redirects, [])

    def _serve(
        self, verb: str, url: str, allow_redirects: bool, history: List[FakeNetworkResponse]
    ) -> FakeNetworkResponse:
        route = self._match(verb, url)
        if route is None:
            raise NoScriptedReply(
                f"{verb} {url} is not scripted; call transport.reply(...) for it. "
                f"Scripted: {sorted(f'{m} {u}' for m, u in self._routes)}"
            )

        self.clock += route.delay
        if route.raises is not None:
            raise route.raises

        if route.redirect_to is not None:
            if len(history) >= self.max_redirects:
                raise RedirectLoop(f"{verb} {url} redirected more than {self.max_redirects} times")
            hop = FakeResponse(
                url=url,
                status_code=route.redirect_status,
                content=b"",
                headers={"location": route.redirect_to},
                reason="Redirect",
            )
            if not allow_redirects:
                hop.history = list(history)
                return hop
            return self._serve(verb, route.redirect_to, allow_redirects, [*history, hop])

        response = route.next_response(url)
        if route.delay:
            response.elapsed = route.delay
        response.history = list(history)
        return response

    def get(self, url, **kwargs):
        return self.request(url, method="GET", **kwargs)

    def post(self, url, **kwargs):
        return self.request(url, method="POST", **kwargs)

    def put(self, url, **kwargs):
        return self.request(url, method="PUT", **kwargs)

    def patch(self, url, **kwargs):
        return self.request(url, method="PATCH", **kwargs)

    def delete(self, url, **kwargs):
        return self.request(url, method="DELETE", **kwargs)

    def head(self, url, **kwargs):
        return self.request(url, method="HEAD", **kwargs)

    # ── routing ─────────────────────────────────────────────────────────────

    def _route(self, method: str, url: str) -> _Route:
        key = (method.upper(), url)
        return self._routes.setdefault(key, _Route())

    def _match(self, verb: str, url: str) -> Optional[_Route]:
        return self._routes.get((verb, url)) or self._routes.get(("*", url))


class FakeNetworkManager:
    """Fake NetworkManager — requests-like, returns canned responses, captures requests."""

    def __init__(
        self,
        responses: Optional[Dict[str, FakeNetworkResponse]] = None,
        headers: Optional[Dict[str, str]] = None,
        calls: Optional[CallLog] = None,
    ):
        self.responses = responses or {}
        self.requests: List[Dict[str, Any]] = []
        self.downloads: List[Tuple[str, str]] = []
        self.headers: Dict[str, str] = dict(headers or {})
        self.calls = call_log(calls)
        self.auth_cfg: Optional[str] = None
        self.timeout: int = 15000

    def _match_response(self, url: str) -> FakeNetworkResponse:
        if url in self.responses:
            return self.responses[url]
        for pattern, resp in self.responses.items():
            if pattern in url:
                return resp
        # Default mock
        return FakeNetworkResponse(url=url, status_code=200, content=b'{"mock": true}')

    def request(
        self,
        url,
        method="GET",
        data=None,
        json=None,
        headers=None,
        params=None,
        auth_cfg=None,
        blocking=True,
        timeout=None,
        **kwargs,
    ):
        full_url = _build_url(url, params)
        all_headers = dict(self.headers)
        if headers:
            all_headers.update(headers)
        self.requests.append(
            {
                "url": full_url,
                "original_url": url,
                "method": method,
                "data": data,
                "json": json,
                "headers": all_headers,
                "params": params,
                "auth_cfg": auth_cfg,
                "timeout": timeout,
                "kwargs": kwargs,
            }
        )
        self.calls.record("network", str(method).lower(), url=full_url, params=params, data=data, json=json)
        return self._match_response(full_url)

    def get(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="GET", params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def post(self, url, data=None, json=None, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="POST", data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def put(self, url, data=None, json=None, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="PUT", data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def patch(self, url, data=None, json=None, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="PATCH", data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def delete(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="DELETE", params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def head(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="HEAD", params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def options(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="OPTIONS", params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def download(self, url, dest_path, progress_callback=None, auth_cfg=None, timeout=None, params=None, **kwargs):
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.downloads.append((url, str(dest_path)))
        resp = self.request(url, params=params, auth_cfg=auth_cfg, timeout=timeout, **kwargs)
        dest.write_bytes(resp.content)
        if progress_callback:
            progress_callback(100)
        return dest

    def fetch(self, url, params=None, auth_cfg=None):
        full_url = _build_url(url, params)
        return FakeContentFetcher(full_url, response=self.request(full_url, auth_cfg=auth_cfg))

    def fetch_blocking(self, url, params=None, auth_cfg=None, timeout=None):
        full_url = _build_url(url, params)
        return self.request(full_url, auth_cfg=auth_cfg, timeout=timeout)

    def session(self, **kwargs):
        return FakeSession(responses=self.responses, **kwargs)

    @classmethod
    def instance(cls, **kwargs):
        # For singleton pattern compatibility
        return cls(**kwargs)


class FakeSession(FakeNetworkManager):
    """Fake Session — requests-like Session for testing."""

    def __init__(self, responses=None, auth_cfg=None, timeout=15000, headers=None, params=None, verify=True):
        super().__init__(responses=responses, headers=headers)
        self.auth_cfg = auth_cfg
        self.timeout = timeout
        self.params = dict(params or {})
        self.verify = verify
        self.cookies: Dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        pass

    def request(self, method, url, params=None, data=None, json=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        # Merge session params/headers
        merged_params = dict(self.params)
        if params:
            merged_params.update(params)
        merged_headers = dict(self.headers)
        if headers:
            merged_headers.update(headers)
        return super().request(
            url,
            method=method,
            data=data,
            json=json,
            params=merged_params if merged_params else None,
            headers=merged_headers,
            auth_cfg=auth_cfg or self.auth_cfg,
            timeout=timeout or self.timeout,
            **kwargs,
        )

    # Override verb methods to use method-first signature
    def get(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("GET", url, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def post(self, url, data=None, json=None, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("POST", url, data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def put(self, url, data=None, json=None, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("PUT", url, data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def patch(self, url, data=None, json=None, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("PATCH", url, data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def delete(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("DELETE", url, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def head(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("HEAD", url, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def options(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("OPTIONS", url, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)


class FakeContentFetcher:
    """Fake ContentFetcher — requests-like params support."""

    def __init__(self, url="", response: Optional[FakeNetworkResponse] = None, params=None):
        self.url = _build_url(url, params) if params else url
        self._response = response or FakeNetworkResponse(url=self.url)
        self._finished_callbacks: List[Callable] = []

    def fetch(self, url, params=None):
        self.url = _build_url(url, params) if params else url
        for cb in self._finished_callbacks:
            try:
                cb()
            except Exception:
                pass

    def fetch_blocking(self, url, params=None, timeout=None):
        self.url = _build_url(url, params) if params else url
        return self._response

    def content_as_string(self):
        return self._response.text

    def content_as_bytes(self):
        return self._response.content

    @property
    def finished(self):
        class _MockSignal:
            def __init__(self, outer):
                self.outer = outer

            def connect(self, cb):
                self.outer._finished_callbacks.append(cb)
                try:
                    cb()
                except Exception:
                    pass

        return _MockSignal(self)

    @property
    def reply(self):
        return None


def fake_network_manager_factory(responses=None, **kwargs):
    return FakeNetworkManager(responses, **kwargs)


def fake_network_response_factory(**kwargs):
    return FakeNetworkResponse(**kwargs)


def fake_content_fetcher_factory(**kwargs):
    return FakeContentFetcher(**kwargs)


def fake_session_factory(responses=None, **kwargs):
    return FakeSession(responses, **kwargs)


def fake_network_transport_factory(**kwargs):
    return FakeNetworkTransport(**kwargs)


__all__ = [
    "FakeNetworkResponse",
    "FakeResponse",
    "FakeNetworkTransport",
    "FakeNetworkManager",
    "FakeSession",
    "FakeContentFetcher",
    "NoScriptedReply",
    "RedirectLoop",
    "fake_network_manager_factory",
    "fake_network_response_factory",
    "fake_content_fetcher_factory",
    "fake_session_factory",
    "fake_network_transport_factory",
]
