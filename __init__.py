"""Kagi web search plugin.

Registers the web backend and a filtered search tool.
"""

from __future__ import annotations

from . import provider, schemas, tools


def register(ctx) -> None:
    """Called once by the plugin loader."""
    ctx.register_web_search_provider(provider.KagiWebSearchProvider())
    ctx.register_tool(
        name="kagi_search",
        toolset="web",
        schema=schemas.KAGI_SEARCH_SCHEMA,
        handler=tools.kagi_search,
        check_fn=tools.kagi_key_present,
        emoji="🔍",
    )
