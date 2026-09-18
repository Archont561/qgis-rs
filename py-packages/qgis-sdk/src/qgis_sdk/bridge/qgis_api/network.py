"""qgis_sdk.bridge.qgis_api.network — network via QGIS NAM for JS."""

from __future__ import annotations

from typing import Any, Dict, Optional


class NetworkAPI:
    def fetch(self, url: str, method: str = "GET", headers: Dict[str, str] = None, body: str = None, auth_cfg: str = None) -> Dict[str, Any]:
        """Makes network request via QgsNetworkAccessManager (respects QGIS proxy, auth).

        Returns dict with status, headers, body, ok.
        """
        headers = headers or {}
        try:
            from qgis_sdk.network import Session
            sess = Session(auth_cfg=auth_cfg, headers=headers)
            # body may be string, convert
            data = body
            resp = sess.request(method, url, data=data, headers=headers, auth_cfg=auth_cfg)
            return {
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp.text,
                "ok": resp.ok,
                "url": resp.url,
            }
        except Exception as e:
            # Fallback urllib
            try:
                import urllib.request
                req = urllib.request.Request(url, data=body.encode() if isinstance(body, str) else body, headers=headers or {}, method=method)
                with urllib.request.urlopen(req, timeout=15) as r:
                    content = r.read().decode('utf-8', errors='ignore')
                    return {
                        "status": r.getcode(),
                        "headers": dict(r.getheaders()),
                        "body": content,
                        "ok": 200 <= r.getcode() < 400,
                        "url": url,
                    }
            except Exception as e2:
                return {
                    "status": 0,
                    "headers": {},
                    "body": "",
                    "ok": False,
                    "error": str(e2),
                    "url": url,
                }

    def get(self, url: str, headers: Dict[str, str] = None, auth_cfg: str = None) -> Dict[str, Any]:
        return self.fetch(url, method="GET", headers=headers, auth_cfg=auth_cfg)

    def post(self, url: str, body: str = None, headers: Dict[str, str] = None, auth_cfg: str = None) -> Dict[str, Any]:
        return self.fetch(url, method="POST", headers=headers, body=body, auth_cfg=auth_cfg)
