"""Kagi v1 API client.

Env vars::

    KAGI_API_KEY=...     # https://kagi.com/api/keys (required)
    KAGI_BASE_URL=...     # optional override of the https://kagi.com/api root
"""

from __future__ import annotations

import os
from typing import Any, Dict, List


def kagi_base_url() -> str:
    # API root only; the version segment (/v1) is appended per endpoint.
    return os.getenv("KAGI_BASE_URL", "https://kagi.com/api").rstrip("/")


def kagi_headers() -> Dict[str, str]:
    """Build the bearer auth header.

    Raises ValueError when the key is unset; callers catch it and surface a
    typed error response.
    """
    api_key = os.getenv("KAGI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "KAGI_API_KEY environment variable not set. "
            "Get your API key at https://kagi.com/api/keys"
        )
    return {"Authorization": f"Bearer {api_key}"}


def build_search_body(query: str, **fields: Any) -> Dict[str, Any]:
    """Assemble a Kagi ``/search`` request body.

    Starts from ``query``, adds any truthy ``fields`` (``limit``, ``filters``,
    ``lens_id``, ...), and applies the ``KAGI_SAFE_SEARCH=off`` opt-out. Kagi
    defaults safe search on, so the param is only sent to disable it. Callers
    decide their own limit semantics and pass the resolved value (or omit it).
    """
    body: Dict[str, Any] = {"query": query}
    for key, value in fields.items():
        if value:
            body[key] = value
    if os.getenv("KAGI_SAFE_SEARCH", "").strip().lower() == "off":
        body["safe_search"] = False
    return body


def kagi_post(endpoint: str, body: Dict[str, Any], timeout: float = 60) -> Dict[str, Any]:
    """POST a JSON body to the endpoint and return the parsed response.

    ``endpoint`` is the bare path segment (``"search"``, ``"extract"``); the
    base URL and ``/v1`` prefix are applied here. Raises ValueError (via
    :func:`kagi_headers`) when ``KAGI_API_KEY`` is unset, and httpx errors on
    HTTP failure; callers catch both and surface typed errors.
    """
    import httpx

    resp = httpx.post(
        f"{kagi_base_url()}/v1/{endpoint.lstrip('/')}",
        headers=kagi_headers(),
        json=body,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def normalize_kagi_search_results(response: Dict[str, Any]) -> Dict[str, Any]:
    """Map a search response to ``{success, data: {web: [...]}}``.

    The ``data`` is an *object* whose web/page results live under
    ``data.search`` (an array of ``{url, title, snippet, ...}``). Other
    result types (images, news, videos, related_search, ...) live under
    their own ``data.<kind>`` keys and are ignored here.
    """
    web_results: List[Dict[str, Any]] = []
    data = response.get("data") or {}
    results = data.get("search") if isinstance(data, dict) else None
    for i, item in enumerate(results or []):
        if not isinstance(item, dict):
            continue
        web_results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("snippet", "") or "",
                "position": i + 1,
            }
        )
    return {"success": True, "data": {"web": web_results}}
