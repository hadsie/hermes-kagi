"""Kagi web search backend plugin.

Registers Kagi as a web search + extract backend, powering the built-in
web_search / web_extract tools.
"""

from __future__ import annotations

from . import provider


def register(ctx) -> None:
    """Called once by the plugin loader."""
    ctx.register_web_search_provider(provider.KagiWebSearchProvider())
