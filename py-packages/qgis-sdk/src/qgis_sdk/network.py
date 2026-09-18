"""
qgis_sdk.network — Pythonic wrapper around QgsNetworkAccessManager and QgsNetworkContentFetcher.

Now uses qgis_sdk._qt funnel for PyQt6/PySide6 support, and run_loop() instead of exec_().
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse


# ── Exceptions (requests-like) ──────────────────────────────────────────────

class RequestException(Exception):
    def __init__(self, message: str, response: Optional["NetworkResponse"] = None, request: Optional[Any] = None):
        super().__init__(message)
        self.response = response
        self.request = request


class HTTPError(RequestException):
    pass


class ConnectionError(RequestException):
    pass


class Timeout(RequestException):
    pass


class TooManyRedirects(RequestException):
    pass


NetworkError = RequestException


# ── Response ────────────────────────────────────────────────────────────────

@dataclass
class NetworkResponse:
    url: str
    status_code: int = 200
    content: bytes = b""
    headers: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    error_code: int = 0
    encoding: str = "utf-8"
    elapsed: float = 0.0
    reason: Optional[str] = None
    history: List["NetworkResponse"] = field(default_factory=list)
    cookies: Dict[str, str] = field(default_factory=dict)
    request: Optional[Any] = None

    def __post_init__(self):
        if self.reason is None:
            self.reason = _reason_for_status(self.status_code)

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 400

    @property
    def text(self) -> str:
        try:
            enc = self.encoding or "utf-8"
            return self.content.decode(enc)
        except Exception:
            try:
                return self.content.decode("utf-8")
            except Exception:
                return self.content.decode("latin-1", errors="ignore")

    @property
    def apparent_encoding(self) -> str:
        return "utf-8"

    def json(self) -> Any:
        try:
            return json.loads(self.text)
        except json.JSONDecodeError as e:
            raise RequestException(f"Failed to decode JSON: {e}", response=self) from e

    def raise_for_status(self):
        if not self.ok:
            msg = f"{self.status_code} {self.reason}: {self.error or self.text[:200]} for url: {self.url}"
            raise HTTPError(msg, response=self)

    def iter_content(self, chunk_size: int = 1024) -> Iterator[bytes]:
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i : i + chunk_size]

    def iter_lines(self, chunk_size: int = 1024, decode_unicode: bool = False) -> Iterator[Union[bytes, str]]:
        lines = self.content.split(b"\n")
        for line in lines:
            if decode_unicode:
                yield line.decode(self.encoding or "utf-8", errors="ignore")
            else:
                yield line

    @property
    def is_redirect(self) -> bool:
        return self.status_code in (301, 302, 303, 307, 308)

    @property
    def is_permanent_redirect(self) -> bool:
        return self.status_code in (301, 308)

    def __bool__(self):
        return self.ok

    def __repr__(self):
        return f"<NetworkResponse [{self.status_code}]>"


def _reason_for_status(code: int) -> str:
    reasons = {
        200: "OK", 201: "Created", 204: "No Content",
        301: "Moved Permanently", 302: "Found", 304: "Not Modified",
        400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
        405: "Method Not Allowed", 408: "Request Timeout", 409: "Conflict", 429: "Too Many Requests",
        500: "Internal Server Error", 502: "Bad Gateway", 503: "Service Unavailable", 504: "Gateway Timeout",
    }
    return reasons.get(code, "")


# ── Low-level QGIS access (lazy) ────────────────────────────────────────────

def _get_qgis_network_manager():
    try:
        from qgis.core import QgsNetworkAccessManager  # type: ignore
        return QgsNetworkAccessManager.instance()
    except ImportError:
        return None


def _get_qgis_fetcher():
    try:
        from qgis.core import QgsNetworkContentFetcher  # type: ignore
        return QgsNetworkContentFetcher
    except ImportError:
        return None


def _get_qgis_fetcher_task():
    try:
        from qgis.core import QgsNetworkContentFetcherTask  # type: ignore
        return QgsNetworkContentFetcherTask
    except ImportError:
        return None


# ── Helpers ─────────────────────────────────────────────────────────────────

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


def _prepare_data(
    data: Optional[Union[bytes, str, dict]] = None,
    json_data: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[bytes], Dict[str, str]]:
    headers = dict(headers or {})
    req_data: Optional[bytes] = None

    if json_data is not None:
        req_data = json.dumps(json_data).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    elif data is not None:
        if isinstance(data, dict):
            req_data = urlencode(data, doseq=True).encode("utf-8")
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        elif isinstance(data, str):
            req_data = data.encode("utf-8")
        else:
            req_data = data

    return req_data, headers


def _fallback_request(
    url: str,
    method: str = "GET",
    data: Optional[Union[bytes, str, dict]] = None,
    json_data: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 15000,
) -> NetworkResponse:
    import urllib.request
    import urllib.error

    url = _build_url(url, params)
    req_data, headers = _prepare_data(data, json_data, headers)

    req = urllib.request.Request(url, data=req_data, headers=headers or {}, method=method.upper())

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout / 1000.0) as resp:
            content = resp.read()
            status = resp.getcode()
            resp_headers = {k.lower(): v for k, v in resp.getheaders()}
            elapsed = time.time() - start
            return NetworkResponse(
                url=url, status_code=status, content=content, headers=resp_headers, elapsed=elapsed
            )
    except urllib.error.HTTPError as e:
        content = e.read() if hasattr(e, "read") else b""
        elapsed = time.time() - start
        return NetworkResponse(
            url=url,
            status_code=e.code,
            content=content,
            error=str(e),
            error_code=e.code,
            elapsed=elapsed,
            headers={k.lower(): v for k, v in e.headers.items()} if hasattr(e, "headers") else {},
        )
    except Exception as e:
        elapsed = time.time() - start
        return NetworkResponse(url=url, status_code=0, content=b"", error=str(e), error_code=-1, elapsed=elapsed)


# ── Qt helpers via _qt funnel ───────────────────────────────────────────────

def _get_qt_for_network():
    """Get Qt classes via _qt funnel, handling both PyQt6 and PySide6."""
    try:
        from ._qt import QUrl, QEventLoop, QTimer, QNetworkRequest, QNetworkAccessManager, QNetworkReply, run_loop
        return {
            "QUrl": QUrl,
            "QEventLoop": QEventLoop,
            "QTimer": QTimer,
            "QNetworkRequest": QNetworkRequest,
            "QNetworkAccessManager": QNetworkAccessManager,
            "QNetworkReply": QNetworkReply,
            "run_loop": run_loop,
        }
    except ImportError:
        return None


# ── ContentFetcher ──────────────────────────────────────────────────────────

class ContentFetcher:
    def __init__(self, auth_cfg: Optional[str] = None):
        self.auth_cfg = auth_cfg
        self._qgis_fetcher = None
        self._response: Optional[NetworkResponse] = None
        self._finished_callbacks: List[Callable] = []

        FetcherClass = _get_qgis_fetcher()
        if FetcherClass:
            try:
                self._qgis_fetcher = FetcherClass()
                if hasattr(self._qgis_fetcher, "finished"):
                    self._qgis_fetcher.finished.connect(self._on_qgis_finished)
            except Exception:
                self._qgis_fetcher = None

    def _on_qgis_finished(self):
        for cb in self._finished_callbacks:
            try:
                cb()
            except Exception:
                pass

    def fetch(self, url: str, params: Optional[Dict[str, Any]] = None):
        url = _build_url(url, params)
        if self._qgis_fetcher:
            try:
                qt = _get_qt_for_network()
                QUrl = qt["QUrl"] if qt else None
                if QUrl is None:
                    from qgis.PyQt.QtCore import QUrl as QUrlFallback  # type: ignore
                    QUrl = QUrlFallback
                self._qgis_fetcher.fetchContent(QUrl(url))
                return
            except Exception:
                pass

        self._response = _fallback_request(url)
        self._on_qgis_finished()

    def fetch_blocking(self, url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 15000) -> NetworkResponse:
        url = _build_url(url, params)
        if self._qgis_fetcher:
            try:
                qt = _get_qt_for_network()
                if qt:
                    QUrl = qt["QUrl"]
                    QEventLoop = qt["QEventLoop"]
                    QTimer = qt["QTimer"]
                    QNetworkRequest = qt["QNetworkRequest"]
                    run_loop = qt["run_loop"]
                else:
                    from qgis.PyQt.QtCore import QUrl, QEventLoop, QTimer  # type: ignore
                    from qgis.PyQt.QtNetwork import QNetworkRequest  # type: ignore
                    from qgis_sdk._qt import run_loop  # type: ignore

                loop = QEventLoop()
                self._qgis_fetcher.finished.connect(loop.quit)
                if timeout > 0:
                    QTimer.singleShot(timeout, loop.quit)

                self._qgis_fetcher.fetchContent(QUrl(url))
                run_loop(loop)

                content = b""
                try:
                    if hasattr(self._qgis_fetcher, "contentAsString"):
                        content = self._qgis_fetcher.contentAsString().encode("utf-8")
                    elif hasattr(self._qgis_fetcher, "reply"):
                        reply = self._qgis_fetcher.reply()
                        if reply:
                            content = bytes(reply.readAll())
                except Exception:
                    pass

                status = 200
                try:
                    if hasattr(self._qgis_fetcher, "reply"):
                        reply = self._qgis_fetcher.reply()
                        if reply and hasattr(reply, "attribute"):
                            code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
                            if code:
                                status = int(code)
                except Exception:
                    pass

                self._response = NetworkResponse(url=url, status_code=status, content=content)
                return self._response
            except Exception:
                pass

        self._response = _fallback_request(url, timeout=timeout)
        return self._response

    def content_as_string(self) -> str:
        if self._response:
            return self._response.text
        if self._qgis_fetcher:
            try:
                if hasattr(self._qgis_fetcher, "contentAsString"):
                    return self._qgis_fetcher.contentAsString()
            except Exception:
                pass
        return ""

    def content_as_bytes(self) -> bytes:
        if self._response:
            return self._response.content
        return self.content_as_string().encode("utf-8")

    @property
    def reply(self):
        if self._qgis_fetcher and hasattr(self._qgis_fetcher, "reply"):
            try:
                return self._qgis_fetcher.reply()
            except Exception:
                pass
        return None

    @property
    def finished(self):
        if self._qgis_fetcher and hasattr(self._qgis_fetcher, "finished"):
            return self._qgis_fetcher.finished

        class _MockSignal:
            def __init__(self, outer):
                self.outer = outer

            def connect(self, cb):
                self.outer._finished_callbacks.append(cb)
                if self.outer._response:
                    try:
                        cb()
                    except Exception:
                        pass

        return _MockSignal(self)


# ── Session ─────────────────────────────────────────────────────────────────

class Session:
    def __init__(
        self,
        auth_cfg: Optional[str] = None,
        timeout: int = 15000,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        verify: bool = True,
    ):
        self.auth_cfg = auth_cfg
        self.timeout = timeout
        self.headers: Dict[str, str] = dict(headers or {})
        self.params: Dict[str, Any] = dict(params or {})
        self.verify = verify
        self._qgis_nam = _get_qgis_network_manager()
        self.cookies: Dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        pass

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[bytes, str, dict]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        auth_cfg: Optional[str] = None,
        timeout: Optional[int] = None,
        blocking: bool = True,
        **kwargs,
    ) -> NetworkResponse:
        all_headers = dict(self.headers)
        if headers:
            all_headers.update(headers)

        all_params = dict(self.params)
        if params:
            all_params.update(params)

        url = _build_url(url, all_params if all_params else None)
        req_data, final_headers = _prepare_data(data, json, all_headers)

        timeout = timeout if timeout is not None else self.timeout
        auth_cfg = auth_cfg or self.auth_cfg

        mgr = NetworkManager.instance(auth_cfg=auth_cfg, timeout=timeout)
        return mgr.request(
            url,
            method=method,
            data=req_data,
            headers=final_headers,
            auth_cfg=auth_cfg,
            blocking=blocking,
            timeout=timeout,
        )

    def get(self, url: str, **kwargs) -> NetworkResponse:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, data=None, json=None, **kwargs) -> NetworkResponse:
        return self.request("POST", url, data=data, json=json, **kwargs)

    def put(self, url: str, data=None, json=None, **kwargs) -> NetworkResponse:
        return self.request("PUT", url, data=data, json=json, **kwargs)

    def patch(self, url: str, data=None, json=None, **kwargs) -> NetworkResponse:
        return self.request("PATCH", url, data=data, json=json, **kwargs)

    def delete(self, url: str, **kwargs) -> NetworkResponse:
        return self.request("DELETE", url, **kwargs)

    def head(self, url: str, **kwargs) -> NetworkResponse:
        return self.request("HEAD", url, **kwargs)

    def options(self, url: str, **kwargs) -> NetworkResponse:
        return self.request("OPTIONS", url, **kwargs)

    def fetch(self, url: str, auth_cfg: Optional[str] = None) -> ContentFetcher:
        fetcher = ContentFetcher(auth_cfg=auth_cfg or self.auth_cfg)
        fetcher.fetch(url)
        return fetcher

    def fetch_blocking(self, url: str, auth_cfg: Optional[str] = None, timeout: Optional[int] = None) -> NetworkResponse:
        fetcher = ContentFetcher(auth_cfg=auth_cfg or self.auth_cfg)
        return fetcher.fetch_blocking(url, timeout=timeout or self.timeout)

    def download(
        self,
        url: str,
        dest_path: Union[str, Path],
        progress_callback: Optional[Callable[[int], None]] = None,
        auth_cfg: Optional[str] = None,
        timeout: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Path:
        url = _build_url(url, params)
        mgr = NetworkManager.instance(auth_cfg=auth_cfg or self.auth_cfg, timeout=timeout or self.timeout)
        return mgr.download(url, dest_path, progress_callback=progress_callback, auth_cfg=auth_cfg, timeout=timeout)


# ── NetworkManager ──────────────────────────────────────────────────────────

class NetworkManager:
    _instance: Optional["NetworkManager"] = None

    def __init__(self, auth_cfg: Optional[str] = None, timeout: int = 15000, headers: Optional[Dict[str, str]] = None):
        self.auth_cfg = auth_cfg
        self.timeout = timeout
        self.headers: Dict[str, str] = dict(headers or {})
        self._qgis_nam = _get_qgis_network_manager()
        self._session = Session(auth_cfg=auth_cfg, timeout=timeout, headers=headers)

    @classmethod
    def instance(cls, auth_cfg: Optional[str] = None, timeout: int = 15000, headers: Optional[Dict[str, str]] = None) -> "NetworkManager":
        if cls._instance is None:
            cls._instance = cls(auth_cfg=auth_cfg, timeout=timeout, headers=headers)
        else:
            if auth_cfg is not None:
                cls._instance.auth_cfg = auth_cfg
                cls._instance._session.auth_cfg = auth_cfg
            if timeout is not None:
                cls._instance.timeout = timeout
                cls._instance._session.timeout = timeout
            if headers:
                cls._instance.headers.update(headers)
                cls._instance._session.headers.update(headers)
        return cls._instance

    def setup_proxy_and_cache(self):
        if self._qgis_nam and hasattr(self._qgis_nam, "setupDefaultProxyAndCache"):
            try:
                self._qgis_nam.setupDefaultProxyAndCache()
            except Exception:
                pass

    def fallback_proxy(self):
        if self._qgis_nam and hasattr(self._qgis_nam, "fallbackProxy"):
            try:
                return self._qgis_nam.fallbackProxy()
            except Exception:
                pass
        return None

    def request(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Union[bytes, str, dict]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        auth_cfg: Optional[str] = None,
        blocking: bool = True,
        timeout: Optional[int] = None,
    ) -> NetworkResponse:
        timeout = timeout if timeout is not None else self.timeout
        auth_cfg = auth_cfg or self.auth_cfg

        all_headers = dict(self.headers)
        if headers:
            all_headers.update(headers)

        url = _build_url(url, params)
        req_data, final_headers = _prepare_data(data, json, all_headers)

        if self._qgis_nam and blocking:
            try:
                qt = _get_qt_for_network()
                if qt:
                    QUrl = qt["QUrl"]
                    QEventLoop = qt["QEventLoop"]
                    QTimer = qt["QTimer"]
                    QNetworkRequest = qt["QNetworkRequest"]
                    QNetworkAccessManager = qt["QNetworkAccessManager"]
                    QNetworkReply = qt["QNetworkReply"]
                    run_loop = qt["run_loop"]
                else:
                    from qgis.PyQt.QtCore import QUrl, QEventLoop, QTimer  # type: ignore
                    from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkReply  # type: ignore
                    from qgis_sdk._qt import run_loop  # type: ignore

                req = QNetworkRequest(QUrl(url))
                for k, v in final_headers.items():
                    req.setRawHeader(k.encode("utf-8"), v.encode("utf-8"))

                if method.upper() == "GET":
                    reply = self._qgis_nam.get(req)
                elif method.upper() == "POST":
                    reply = self._qgis_nam.post(req, req_data or b"")
                elif method.upper() == "PUT":
                    reply = self._qgis_nam.put(req, req_data or b"")
                elif method.upper() == "DELETE":
                    reply = self._qgis_nam.deleteResource(req)
                elif method.upper() == "HEAD":
                    reply = self._qgis_nam.createRequest(QNetworkAccessManager.HeadOperation, req)
                elif method.upper() == "PATCH":
                    reply = self._qgis_nam.createRequest(QNetworkAccessManager.CustomOperation, req, req_data)
                    try:
                        reply.setProperty("custom-verb", b"PATCH")
                    except Exception:
                        pass
                else:
                    op_map = {
                        "GET": QNetworkAccessManager.GetOperation,
                        "POST": QNetworkAccessManager.PostOperation,
                        "PUT": QNetworkAccessManager.PutOperation,
                        "DELETE": QNetworkAccessManager.DeleteOperation,
                        "HEAD": QNetworkAccessManager.HeadOperation,
                    }
                    op = op_map.get(method.upper(), QNetworkAccessManager.GetOperation)
                    reply = self._qgis_nam.createRequest(op, req, req_data)

                loop = QEventLoop()
                reply.finished.connect(loop.quit)
                if timeout > 0:
                    QTimer.singleShot(timeout, loop.quit)
                run_loop(loop)

                status = 0
                error = None
                content = b""
                resp_headers = {}

                try:
                    content = bytes(reply.readAll())
                except Exception:
                    pass

                try:
                    code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
                    if code:
                        status = int(code)
                    else:
                        status = 200 if not reply.error() else 0
                except Exception:
                    status = 200

                try:
                    if reply.error() != QNetworkReply.NoError:
                        error = reply.errorString()
                except Exception:
                    pass

                try:
                    for header in reply.rawHeaderList():
                        key = bytes(header).decode("utf-8", errors="ignore").lower()
                        val = bytes(reply.rawHeader(header)).decode("utf-8", errors="ignore")
                        resp_headers[key] = val
                except Exception:
                    pass

                return NetworkResponse(
                    url=url,
                    status_code=status,
                    content=content,
                    headers=resp_headers,
                    error=error if error else None,
                    error_code=reply.error() if hasattr(reply, "error") else 0,
                )
            except Exception as e:
                print(f"[NetworkManager] QGIS request failed, using fallback: {e}")

        return _fallback_request(url, method=method, data=req_data, headers=final_headers, timeout=timeout)

    def get(self, url: str, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs) -> NetworkResponse:
        return self.request(url, method="GET", params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def post(self, url: str, data=None, json=None, headers=None, params=None, auth_cfg=None, timeout=None, **kwargs) -> NetworkResponse:
        return self.request(url, method="POST", data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def put(self, url: str, data=None, json=None, headers=None, params=None, auth_cfg=None, timeout=None, **kwargs) -> NetworkResponse:
        return self.request(url, method="PUT", data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def patch(self, url: str, data=None, json=None, headers=None, params=None, auth_cfg=None, timeout=None, **kwargs) -> NetworkResponse:
        return self.request(url, method="PATCH", data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def delete(self, url: str, headers=None, params=None, auth_cfg=None, timeout=None, **kwargs) -> NetworkResponse:
        return self.request(url, method="DELETE", headers=headers, params=params, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def head(self, url: str, headers=None, params=None, auth_cfg=None, timeout=None, **kwargs) -> NetworkResponse:
        return self.request(url, method="HEAD", headers=headers, params=params, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def options(self, url: str, headers=None, params=None, auth_cfg=None, timeout=None, **kwargs) -> NetworkResponse:
        return self.request(url, method="OPTIONS", headers=headers, params=params, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def fetch(self, url: str, params=None, auth_cfg: Optional[str] = None) -> ContentFetcher:
        fetcher = ContentFetcher(auth_cfg=auth_cfg or self.auth_cfg)
        fetcher.fetch(url, params=params)
        return fetcher

    def fetch_blocking(self, url: str, params=None, auth_cfg: Optional[str] = None, timeout: Optional[int] = None) -> NetworkResponse:
        fetcher = ContentFetcher(auth_cfg=auth_cfg or self.auth_cfg)
        return fetcher.fetch_blocking(url, params=params, timeout=timeout or self.timeout)

    def download(
        self,
        url: str,
        dest_path: Union[str, Path],
        progress_callback: Optional[Callable[[int], None]] = None,
        auth_cfg: Optional[str] = None,
        timeout: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Path:
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = _build_url(url, params)

        if self._qgis_nam:
            try:
                qt = _get_qt_for_network()
                if qt:
                    QUrl = qt["QUrl"]
                    QEventLoop = qt["QEventLoop"]
                    QTimer = qt["QTimer"]
                    QNetworkRequest = qt["QNetworkRequest"]
                    run_loop = qt["run_loop"]
                else:
                    from qgis.PyQt.QtCore import QUrl, QEventLoop, QTimer  # type: ignore
                    from qgis.PyQt.QtNetwork import QNetworkRequest  # type: ignore
                    from qgis_sdk._qt import run_loop  # type: ignore

                req = QNetworkRequest(QUrl(url))
                reply = self._qgis_nam.get(req)

                loop = QEventLoop()
                reply.finished.connect(loop.quit)

                if progress_callback and hasattr(reply, "downloadProgress"):
                    def on_progress(bytes_received, bytes_total):
                        if bytes_total > 0:
                            pct = int(bytes_received * 100 / bytes_total)
                            try:
                                progress_callback(pct)
                            except Exception:
                                pass
                    reply.downloadProgress.connect(on_progress)

                if timeout and timeout > 0:
                    QTimer.singleShot(timeout, loop.quit)
                elif self.timeout > 0:
                    QTimer.singleShot(self.timeout, loop.quit)

                run_loop(loop)

                content = bytes(reply.readAll())
                dest.write_bytes(content)

                if progress_callback:
                    try:
                        progress_callback(100)
                    except Exception:
                        pass

                return dest
            except Exception as e:
                print(f"[NetworkManager] QGIS download failed, using fallback: {e}")

        response = _fallback_request(url, timeout=timeout or self.timeout)
        if not response.ok:
            raise RequestException(f"Download failed: {response.error}", response=response)
        dest.write_bytes(response.content)
        if progress_callback:
            try:
                progress_callback(100)
            except Exception:
                pass
        return dest

    def session(self, **kwargs) -> Session:
        return Session(auth_cfg=kwargs.get("auth_cfg", self.auth_cfg), timeout=kwargs.get("timeout", self.timeout), headers=kwargs.get("headers", self.headers))


class NetworkAccessManager:
    def __init__(self, auth_cfg: Optional[str] = None, timeout: int = 15000, exception_class: Optional[type] = None, headers: Optional[Dict[str, str]] = None):
        self.auth_cfg = auth_cfg
        self.timeout = timeout
        self.exception_class = exception_class or RequestException
        self.headers = dict(headers or {})
        self._nam = NetworkManager.instance(auth_cfg=auth_cfg, timeout=timeout, headers=headers)
        self._session = Session(auth_cfg=auth_cfg, timeout=timeout, headers=headers)

    def request(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Union[bytes, str, dict]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        auth_cfg: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Union[Tuple[NetworkResponse, bytes], NetworkResponse]:
        response = self._nam.request(
            url,
            method=method,
            data=data,
            json=json,
            headers=headers,
            params=params,
            auth_cfg=auth_cfg or self.auth_cfg,
            timeout=timeout or self.timeout,
        )

        if not response.ok:
            raise self.exception_class(f"Request failed {url}: {response.error or response.status_code}", response)

        return response, response.content

    def get(self, url: str, params=None, headers=None, auth_cfg=None, **kwargs) -> NetworkResponse:
        return self._session.get(url, params=params, headers=headers, auth_cfg=auth_cfg or self.auth_cfg, timeout=kwargs.get("timeout", self.timeout))

    def post(self, url: str, data=None, json=None, headers=None, params=None, auth_cfg=None, **kwargs) -> NetworkResponse:
        return self._session.post(url, data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg or self.auth_cfg, timeout=kwargs.get("timeout", self.timeout))

    def put(self, url: str, data=None, json=None, headers=None, params=None, auth_cfg=None, **kwargs) -> NetworkResponse:
        return self._session.put(url, data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg or self.auth_cfg, timeout=kwargs.get("timeout", self.timeout))

    def patch(self, url: str, data=None, json=None, headers=None, params=None, auth_cfg=None, **kwargs) -> NetworkResponse:
        return self._session.patch(url, data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg or self.auth_cfg, timeout=kwargs.get("timeout", self.timeout))

    def delete(self, url: str, headers=None, params=None, auth_cfg=None, **kwargs) -> NetworkResponse:
        return self._session.delete(url, headers=headers, params=params, auth_cfg=auth_cfg or self.auth_cfg, timeout=kwargs.get("timeout", self.timeout))

    def head(self, url: str, headers=None, params=None, auth_cfg=None, **kwargs) -> NetworkResponse:
        return self._session.head(url, headers=headers, params=params, auth_cfg=auth_cfg or self.auth_cfg, timeout=kwargs.get("timeout", self.timeout))


# ── Top-level requests-like functions ───────────────────────────────────────

_default_session = None


def _get_default_session() -> Session:
    global _default_session
    if _default_session is None:
        _default_session = Session()
    return _default_session


def request(method: str, url: str, **kwargs) -> NetworkResponse:
    return _get_default_session().request(method, url, **kwargs)


def get(url: str, params=None, **kwargs) -> NetworkResponse:
    return _get_default_session().get(url, params=params, **kwargs)


def post(url: str, data=None, json=None, **kwargs) -> NetworkResponse:
    return _get_default_session().post(url, data=data, json=json, **kwargs)


def put(url: str, data=None, json=None, **kwargs) -> NetworkResponse:
    return _get_default_session().put(url, data=data, json=json, **kwargs)


def patch(url: str, data=None, json=None, **kwargs) -> NetworkResponse:
    return _get_default_session().patch(url, data=data, json=json, **kwargs)


def delete(url: str, **kwargs) -> NetworkResponse:
    return _get_default_session().delete(url, **kwargs)


def head(url: str, **kwargs) -> NetworkResponse:
    return _get_default_session().head(url, **kwargs)


def options(url: str, **kwargs) -> NetworkResponse:
    return _get_default_session().options(url, **kwargs)


def fetch(url: str, method: str = "GET", **kwargs) -> NetworkResponse:
    return NetworkManager.instance().request(url, method=method, **kwargs)


def fetch_json(url: str, **kwargs) -> Any:
    response = fetch(url, **kwargs)
    response.raise_for_status()
    return response.json()


def fetch_text(url: str, **kwargs) -> str:
    response = fetch(url, **kwargs)
    response.raise_for_status()
    return response.text


def download(url: str, dest: Union[str, Path], **kwargs) -> Path:
    return NetworkManager.instance().download(url, dest, **kwargs)


__all__ = [
    "NetworkManager",
    "NetworkAccessManager",
    "ContentFetcher",
    "NetworkResponse",
    "NetworkError",
    "RequestException",
    "HTTPError",
    "ConnectionError",
    "Timeout",
    "TooManyRedirects",
    "Session",
    "request",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "head",
    "options",
    "fetch",
    "fetch_json",
    "fetch_text",
    "download",
]
