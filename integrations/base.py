"""Base HTTP client for integrations with rate-limit and error handling."""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from core.logger import get_logger

logger = get_logger("integrations.base")


class IntegrationError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(IntegrationError):
    def __init__(self, message: str, retry_after: float = 60.0) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class AuthError(IntegrationError):
    pass


class BaseClient:
    """Shared HTTP client helpers."""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        timeout: float = 30.0,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._default_headers = headers or {}
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            headers = dict(self._default_headers)
            if self.token:
                headers.setdefault("Authorization", self._auth_header())
            self._client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    def _auth_header(self) -> str:
        return f"Bearer {self.token}"

    def close(self) -> None:
        if self._client and not self._client.is_closed:
            self._client.close()
            self._client = None

    def request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json: Optional[Any] = None,
        max_retries: int = 2,
    ) -> Any:
        client = self._get_client()
        url = path if path.startswith("http") else path
        last_exc: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                resp = client.request(method, url, params=params, json=json)
                if resp.status_code == 401 or resp.status_code == 403:
                    raise AuthError(f"Authentication failed ({resp.status_code})", resp.status_code)
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", 60))
                    if attempt < max_retries:
                        logger.warning("Rate limited – sleeping %.1fs", retry_after)
                        time.sleep(min(retry_after, 120))
                        continue
                    raise RateLimitError("Rate limit exceeded", retry_after)
                if resp.status_code >= 400:
                    raise IntegrationError(
                        f"HTTP {resp.status_code}: {resp.text[:200]}",
                        resp.status_code,
                    )
                if resp.status_code == 204 or not resp.content:
                    return None
                return resp.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise IntegrationError(f"Network error: {exc}") from exc
        if last_exc:
            raise IntegrationError(str(last_exc)) from last_exc
        raise IntegrationError("Request failed")

    def get(self, path: str, params: Optional[dict] = None) -> Any:
        return self.request("GET", path, params=params)

    def get_paginated(
        self,
        path: str,
        params: Optional[dict] = None,
        items_key: str = "values",
        max_pages: int = 10,
    ) -> list[Any]:
        """Generic pagination helper – subclasses may override."""
        params = dict(params or {})
        results: list[Any] = []
        page = 1
        while page <= max_pages:
            params["page"] = page
            data = self.get(path, params=params)
            if not data:
                break
            items = data.get(items_key, []) if isinstance(data, dict) else data
            if not items:
                break
            results.extend(items)
            # Stop if fewer items than page size
            if isinstance(data, dict):
                size = data.get("pagelen") or data.get("per_page") or len(items)
                if len(items) < size:
                    break
            else:
                break
            page += 1
        return results
