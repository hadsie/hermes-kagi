"""Tool schemas for the Kagi plugin (what the LLM sees).

Separated from tools.py per the build-a-hermes-plugin guide: schemas
describe the tools for the model; tools.py implements the handlers.
"""

from __future__ import annotations

from typing import Any, Dict


KAGI_SEARCH_SCHEMA: Dict[str, Any] = {
    "name": "kagi_search",
    "description": (
        "Search the web via Kagi with optional date-range (after/before, "
        "ISO YYYY-MM-DD) and lens filters. Use when you need results "
        "constrained to a time window or a category lens."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."},
            "after": {
                "type": "string",
                "description": (
                    "Only return results published or updated on or after this date. "
                    "ISO format YYYY-MM-DD, e.g. '2026-06-01'."
                ),
            },
            "before": {
                "type": "string",
                "description": (
                    "Only return results published or updated on or before this date. "
                    "ISO format YYYY-MM-DD, e.g. '2026-06-08'."
                ),
            },
            "lens_id": {
                "type": "string",
                "description": "Optional Kagi lens to scope the search to a category.",
                "enum": [
                    "forums", "edu", "pdf", "small_web", "programming",
                    "academic", "fediverse", "usenet_archive",
                ],
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (1-1024). Omit to use the Kagi default.",
            },
        },
        "required": ["query"],
    },
}
