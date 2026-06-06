"""Test bootstrap for the Kagi plugin.

The plugin ships as a clone-and-install repo, so its tests must run without a
full Hermes checkout on the path. We therefore:

1. Provide the Hermes boundary modules the plugin imports
   (``agent.web_search_provider`` and ``tools.interrupt``). The real modules
   are used when importable; otherwise faithful stubs stand in.
2. Load the hyphenated ``web-kagi`` directory as the ``web_kagi`` package,
   the same way the Hermes plugin loader does (relative imports resolve).
"""

from __future__ import annotations

import abc
import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def _ensure_module(name: str, build: "callable") -> None:
    """Import ``name`` if it exists; otherwise register a stub built by ``build``."""
    try:
        importlib.import_module(name)
    except ImportError:
        build()


def _register_submodule(parent: ModuleType, parent_name: str, attr: str, mod: ModuleType) -> None:
    """Register a stub submodule so both ``import`` and attribute access work.

    Setting it on the parent package is what lets ``monkeypatch.setattr`` resolve
    a dotted target like ``tools.interrupt.is_interrupted``.
    """
    setattr(parent, attr, mod)
    sys.modules[f"{parent_name}.{attr}"] = mod


def _stub_agent() -> None:
    pkg = sys.modules.setdefault("agent", ModuleType("agent"))
    pkg.__path__ = []  # mark as a package so submodule import works
    mod = ModuleType("agent.web_search_provider")

    class WebSearchProvider(abc.ABC):
        @property
        @abc.abstractmethod
        def name(self) -> str: ...

        @abc.abstractmethod
        def is_available(self) -> bool: ...

    mod.WebSearchProvider = WebSearchProvider
    _register_submodule(pkg, "agent", "web_search_provider", mod)


def _stub_tools() -> None:
    pkg = sys.modules.setdefault("tools", ModuleType("tools"))
    pkg.__path__ = []

    interrupt = ModuleType("tools.interrupt")
    interrupt.is_interrupted = lambda: False
    _register_submodule(pkg, "tools", "interrupt", interrupt)


_ensure_module("agent.web_search_provider", _stub_agent)
_ensure_module("tools.interrupt", _stub_tools)


def _load_plugin_package() -> ModuleType:
    """Load the plugin dir as the ``web_kagi`` package."""
    if "web_kagi" in sys.modules:
        return sys.modules["web_kagi"]
    spec = importlib.util.spec_from_file_location(
        "web_kagi",
        PLUGIN_ROOT / "__init__.py",
        submodule_search_locations=[str(PLUGIN_ROOT)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["web_kagi"] = module
    spec.loader.exec_module(module)
    return module


_load_plugin_package()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Each test starts with no Kagi env vars, regardless of the shell."""
    for var in ("KAGI_API_KEY", "KAGI_BASE_URL", "KAGI_SAFE_SEARCH"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.setenv("KAGI_API_KEY", "test-key-123")


@pytest.fixture
def kagi_api(monkeypatch):
    """Mock ``httpx.post`` at the boundary and record every request.

    - search calls (body has ``query``) return ``box["search"]``.
    - extract calls (body has ``pages``) return ``box["extract"]`` when set,
      else a synthesized one-doc-per-URL response.
    - set ``box["raise"]`` to an exception to fail ``raise_for_status()``.
    """
    import httpx

    calls = []
    box = {"search": {"data": {"search": []}}, "extract": None, "raise": None}

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            if box["raise"] is not None:
                raise box["raise"]

        def json(self):
            return self._payload

    def fake_post(url, headers=None, json=None, timeout=None):
        body = json or {}
        calls.append({"url": url, "headers": headers, "json": body, "timeout": timeout})
        if "pages" in body:
            if box["extract"] is not None:
                return _Resp(box["extract"])
            return _Resp(
                {"data": [{"url": p["url"], "markdown": f"# {p['url']}"} for p in body["pages"]]}
            )
        return _Resp(box["search"])

    monkeypatch.setattr(httpx, "post", fake_post)
    return SimpleNamespace(calls=calls, box=box)
