"""Thin HTTP client for the vbee.vn API. Injectable transport for tests."""

from __future__ import annotations

import json
from typing import Any

import httpx

from .config import VOICES_BASE, Settings
from .errors import VbeeAPIError, error_from_response

DEFAULT_TIMEOUT = 120.0


def _headers(settings: Settings, content_type: str | None = None) -> dict[str, str]:
    assert settings.app_id and settings.token  # guarded by require_credentials
    headers = {
        "Authorization": f"Bearer {settings.token}",
        "App-Id": settings.app_id,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _client(client: httpx.Client | None, timeout: float) -> httpx.Client:
    return client if client is not None else httpx.Client(timeout=timeout)


def _check(resp: httpx.Response) -> httpx.Response:
    if resp.status_code >= 400:
        raise error_from_response(resp.status_code, resp.content)
    return resp


def post_json(
    settings: Settings,
    path: str,
    body: dict[str, Any],
    *,
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> httpx.Response:
    url = f"{settings.api_base}{path}"
    owns = client is None
    c = _client(client, timeout)
    try:
        resp = c.post(url, content=json.dumps(body), headers=_headers(settings, "application/json"))
        return _check(resp)
    except httpx.HTTPError as exc:
        raise VbeeAPIError(code="NETWORK_ERROR", message=str(exc)) from exc
    finally:
        if owns:
            c.close()


def post_multipart(
    settings: Settings,
    path: str,
    data: dict[str, Any],
    files: dict[str, Any] | None = None,
    *,
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> httpx.Response:
    url = f"{settings.api_base}{path}"
    owns = client is None
    c = _client(client, timeout)
    try:
        # Force multipart/form-data even with no file fields (vbee STT expects it).
        multipart: dict[str, Any] = {k: (None, str(v)) for k, v in (data or {}).items()}
        if files:
            multipart.update(files)
        resp = c.post(url, files=multipart, headers=_headers(settings))
        return _check(resp)
    except httpx.HTTPError as exc:
        raise VbeeAPIError(code="NETWORK_ERROR", message=str(exc)) from exc
    finally:
        if owns:
            c.close()


def get_json(
    settings: Settings,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    base: str | None = None,
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    url = f"{base or settings.api_base}{path}"
    owns = client is None
    c = _client(client, timeout)
    try:
        resp = c.get(url, params=params, headers=_headers(settings))
        _check(resp)
        try:
            return resp.json()
        except Exception as exc:
            raise VbeeAPIError(code="INVALID_JSON", message="Response was not valid JSON") from exc
    except httpx.HTTPError as exc:
        raise VbeeAPIError(code="NETWORK_ERROR", message=str(exc)) from exc
    finally:
        if owns:
            c.close()


def get_voices(
    settings: Settings,
    params: dict[str, Any],
    *,
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    return get_json(
        settings, "/voices", params=params, base=VOICES_BASE, client=client, timeout=timeout
    )
