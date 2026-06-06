"""Kagi web search + extraction backend.

Two capabilities, both on Kagi's current ``v1`` API:

- ``supports_search()``  -> True   (Kagi Search API,  ``POST /api/v1/search``)
- ``supports_extract()`` -> True   (Kagi Extract API, ``POST /api/v1/extract``)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from agent.web_search_provider import WebSearchProvider

from .client import build_search_body, kagi_post, normalize_kagi_search_results

logger = logging.getLogger(__name__)

# Kagi's Extract API processes at most this many URLs per request.
_EXTRACT_MAX_URLS = 10


class KagiWebSearchProvider(WebSearchProvider):
    """Kagi search + extract provider (v1 API)."""

    @property
    def name(self) -> str:
        return "kagi"

    @property
    def display_name(self) -> str:
        return "Kagi"

    def is_available(self) -> bool:
        """Return True when ``KAGI_API_KEY`` is set to a non-empty value.

        Cheap, no-network check per the ABC contract.
        """
        return bool(os.getenv("KAGI_API_KEY", "").strip())

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return True

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Execute a Kagi search via the v1 Search API."""
        try:
            from tools.interrupt import is_interrupted

            if is_interrupted():
                return {"success": False, "error": "Interrupted"}

            # v1 search is POST with a JSON body; "limit" caps results (1-1024).
            body = build_search_body(query, limit=max(1, min(limit, 1024)))
            logger.info("Kagi search: '%s' (limit=%d)", query, limit)

            return normalize_kagi_search_results(kagi_post("search", body))
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001 — including httpx errors
            logger.warning("Kagi search error: %s", exc)
            return {"success": False, "error": f"Kagi search failed: {exc}"}

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        """Extract page contents as markdown via the v1 Extract API.

        POST /v1/extract — body ``{"pages": [{"url": ...}, ...]}``, max 10
        URLs per call. Response: ``{"data": [{"url", "markdown", "error"}],
        "errors": [...]}``; ``markdown`` is null when a page fails (with a
        sibling ``error``). URLs are chunked into batches of 10.
        """
        try:
            from tools.interrupt import is_interrupted

            if is_interrupted():
                return [{"url": u, "error": "Interrupted", "title": ""} for u in urls]

            documents: List[Dict[str, Any]] = []

            for start in range(0, len(urls), _EXTRACT_MAX_URLS):
                batch = urls[start:start + _EXTRACT_MAX_URLS]
                logger.info("Kagi extract: %d URL(s)", len(batch))
                response = kagi_post(
                    "extract",
                    {"pages": [{"url": u} for u in batch]},
                    timeout=120,
                )
                data = response.get("data") or []
                for item in data:
                    item = item or {}
                    md = item.get("markdown") or ""
                    url = item.get("url", "")
                    doc: Dict[str, Any] = {
                        "url": url,
                        "title": "",
                        "content": md,
                        "raw_content": md,
                        "metadata": {"sourceURL": url, "extractor": "kagi-v1-extract"},
                    }
                    if item.get("error"):
                        doc["error"] = item["error"]
                    documents.append(doc)
            return documents
        except ValueError as exc:
            return [{"url": u, "title": "", "content": "", "error": str(exc)} for u in urls]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Kagi extract error: %s", exc)
            return [
                {"url": u, "title": "", "content": "", "error": f"Kagi extract failed: {exc}"}
                for u in urls
            ]

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Kagi",
            "badge": "paid",
            "tag": "Premium search + markdown extraction (v1 API).",
            "env_vars": [
                {
                    "key": "KAGI_API_KEY",
                    "prompt": "Kagi API key (bearer token)",
                    "url": "https://kagi.com/api/keys",
                },
            ],
        }
