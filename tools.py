"""Additional kagi search tools

kagi_search — Web search with date and lens filters.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

from .client import kagi_post, normalize_kagi_search_results

logger = logging.getLogger(__name__)


def kagi_key_present() -> bool:
    """check_fn for the tool — keeps it visible in ``hermes tools`` but blocks
    dispatch until KAGI_API_KEY is configured."""
    return bool(os.getenv("KAGI_API_KEY", "").strip())


def kagi_search(args: Dict[str, Any], **_kw: Any) -> str:
    """Filter-aware Kagi search. Returns a tool_result string.

    Supports date-range (after/before) and lens scoping that the generic
    web_search backend can't express. Date strings are ISO YYYY-MM-DD.
    """
    from tools.interrupt import is_interrupted
    from tools.registry import tool_error, tool_result

    if is_interrupted():
        return tool_error("Interrupted")

    query = str(args.get("query") or "").strip()
    if not query:
        return tool_error("query is required")

    try:
        limit = int(args.get("limit") or 10)
    except (TypeError, ValueError):
        limit = 10
    body: Dict[str, Any] = {"query": query, "limit": max(1, min(limit, 50))}

    filters: Dict[str, Any] = {}
    after = str(args.get("after") or "").strip()
    before = str(args.get("before") or "").strip()
    if after:
        filters["after"] = after
    if before:
        filters["before"] = before
    if filters:
        body["filters"] = filters

    lens_id = str(args.get("lens_id") or "").strip()
    if lens_id:
        body["lens_id"] = lens_id

    if os.getenv("KAGI_SAFE_SEARCH", "").strip().lower() == "off":
        body["safe_search"] = False

    try:
        web = normalize_kagi_search_results(kagi_post("search", body)).get("data", {}).get("web", [])
        return tool_result({"results": web, "count": len(web)})
    except ValueError as exc:  # missing KAGI_API_KEY
        return tool_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.warning("kagi_search tool error: %s", exc)
        return tool_error(f"Kagi search failed: {exc}")
