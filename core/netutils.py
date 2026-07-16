"""
Shared HTTP helper used by every investigation module.

Centralizes timeout, retry, user-agent, and error-handling behavior so
individual modules stay focused on parsing results rather than
re-implementing requests boilerplate (and so a flaky network never
crashes the whole app -- it always returns a structured result).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.config import get as config_get
from core.logger import get_logger

log = get_logger("netutils")

try:
    import requests
    from requests.exceptions import RequestException
    _HAS_REQUESTS = True
except ImportError:  # handled gracefully; dependency checker should catch this first
    _HAS_REQUESTS = False
    RequestException = Exception  # type: ignore


@dataclass
class FetchResult:
    ok: bool
    status_code: Optional[int] = None
    text: str = ""
    json_data: Optional[Any] = None
    error: str = ""
    url: str = ""


def _headers() -> Dict[str, str]:
    return {"User-Agent": config_get("network.user_agent", "Geeps-OSINT-Hub/2.0")}


def get(url: str, *, params: Optional[dict] = None, headers: Optional[dict] = None,
        allow_404: bool = True, expect_json: bool = False) -> FetchResult:
    """GET a URL with the app's timeout/retry policy. Never raises."""
    if not _HAS_REQUESTS:
        return FetchResult(ok=False, error="The 'requests' package is not installed.", url=url)

    timeout = config_get("app.request_timeout_seconds", 8)
    max_retries = config_get("app.max_retries", 2)
    verify_tls = config_get("network.verify_tls", True)
    merged_headers = _headers()
    if headers:
        merged_headers.update(headers)

    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(
                url, params=params, headers=merged_headers,
                timeout=timeout, verify=verify_tls,
            )
            if resp.status_code == 404 and allow_404:
                return FetchResult(ok=True, status_code=404, text="", url=url)

            result = FetchResult(ok=resp.ok, status_code=resp.status_code, text=resp.text, url=url)
            if expect_json and resp.ok:
                try:
                    result.json_data = resp.json()
                except ValueError:
                    result.ok = False
                    result.error = "Response was not valid JSON."
            return result
        except RequestException as exc:
            last_error = str(exc)
            log.debug("GET %s attempt %d/%d failed: %s", url, attempt + 1, max_retries + 1, last_error)

    log.warning("GET %s failed after retries: %s", url, last_error)
    return FetchResult(ok=False, error=last_error or "Request failed.", url=url)


def head(url: str, *, headers: Optional[dict] = None) -> FetchResult:
    """HEAD a URL (used for lightweight username-existence checks). Never raises."""
    if not _HAS_REQUESTS:
        return FetchResult(ok=False, error="The 'requests' package is not installed.", url=url)

    timeout = config_get("app.request_timeout_seconds", 8)
    verify_tls = config_get("network.verify_tls", True)
    merged_headers = _headers()
    if headers:
        merged_headers.update(headers)

    try:
        resp = requests.head(
            url, headers=merged_headers, timeout=timeout,
            verify=verify_tls, allow_redirects=True,
        )
        return FetchResult(ok=True, status_code=resp.status_code, url=url)
    except RequestException as exc:
        log.debug("HEAD %s failed: %s", url, exc)
        return FetchResult(ok=False, error=str(exc), url=url)
