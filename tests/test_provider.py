"""Tests for the Kagi web search backend (provider.py)."""

from __future__ import annotations

import httpx
import pytest

from web_kagi.provider import KagiWebSearchProvider


@pytest.fixture
def provider():
    return KagiWebSearchProvider()


class TestCapabilities:
    def test_identity(self, provider):
        assert provider.name == "kagi"
        assert provider.display_name == "Kagi"

    def test_supports_both_search_and_extract(self, provider):
        assert provider.supports_search() is True
        assert provider.supports_extract() is True

    def test_is_available_tracks_key_presence(self, provider, monkeypatch):
        assert provider.is_available() is False
        monkeypatch.setenv("KAGI_API_KEY", "k")
        assert provider.is_available() is True

    def test_is_available_false_for_blank_key(self, provider, monkeypatch):
        monkeypatch.setenv("KAGI_API_KEY", "   ")
        assert provider.is_available() is False


class TestSearch:
    def test_returns_normalized_results(self, provider, with_key, kagi_api):
        kagi_api.box["search"] = {"data": {"search": [{"title": "T", "url": "u", "snippet": "s"}]}}
        result = provider.search("query")
        assert result["success"] is True
        assert result["data"]["web"] == [
            {"title": "T", "url": "u", "description": "s", "position": 1}
        ]

    def test_clamps_limit_to_kagi_ceiling(self, provider, with_key, kagi_api):
        provider.search("q", limit=5000)
        assert kagi_api.calls[-1]["json"]["limit"] == 1024

    def test_floors_limit_at_one(self, provider, with_key, kagi_api):
        provider.search("q", limit=0)
        assert kagi_api.calls[-1]["json"]["limit"] == 1

    def test_omits_safe_search_by_default(self, provider, with_key, kagi_api):
        provider.search("q")
        assert "safe_search" not in kagi_api.calls[-1]["json"]

    def test_disables_safe_search_when_env_is_off(self, provider, with_key, monkeypatch, kagi_api):
        monkeypatch.setenv("KAGI_SAFE_SEARCH", "OFF")
        provider.search("q")
        assert kagi_api.calls[-1]["json"]["safe_search"] is False

    def test_other_safe_search_values_are_ignored(self, provider, with_key, monkeypatch, kagi_api):
        monkeypatch.setenv("KAGI_SAFE_SEARCH", "false")
        provider.search("q")
        assert "safe_search" not in kagi_api.calls[-1]["json"]

    def test_unconfigured_returns_error_response(self, provider, kagi_api):
        result = provider.search("q")
        assert result["success"] is False
        assert "KAGI_API_KEY" in result["error"]
        assert kagi_api.calls == []

    def test_http_failure_returns_error_response(self, provider, with_key, kagi_api):
        kagi_api.box["raise"] = httpx.HTTPError("503")
        result = provider.search("q")
        assert result["success"] is False
        assert "Kagi search failed" in result["error"]


class TestExtract:
    def test_maps_markdown_to_content_and_raw_content(self, provider, with_key, kagi_api):
        kagi_api.box["extract"] = {"data": [{"url": "https://a.test", "markdown": "# Hello"}]}
        docs = provider.extract(["https://a.test"])
        assert len(docs) == 1
        doc = docs[0]
        assert doc["url"] == "https://a.test"
        assert doc["content"] == "# Hello"
        assert doc["raw_content"] == "# Hello"
        assert doc["metadata"]["sourceURL"] == "https://a.test"
        assert "error" not in doc

    def test_per_page_error_is_surfaced(self, provider, with_key, kagi_api):
        kagi_api.box["extract"] = {"data": [{"url": "u", "markdown": None, "error": "blocked"}]}
        doc = provider.extract(["u"])[0]
        assert doc["error"] == "blocked"
        assert doc["content"] == ""

    def test_batches_urls_in_groups_of_ten(self, provider, with_key, kagi_api):
        urls = [f"https://x{i}.test" for i in range(11)]
        docs = provider.extract(urls)
        assert len(kagi_api.calls) == 2
        assert len(kagi_api.calls[0]["json"]["pages"]) == 10
        assert len(kagi_api.calls[1]["json"]["pages"]) == 1
        assert len(docs) == 11

    def test_extract_uses_extended_timeout(self, provider, with_key, kagi_api):
        provider.extract(["u"])
        assert kagi_api.calls[-1]["timeout"] == 120

    def test_unconfigured_returns_per_url_error_dicts(self, provider, kagi_api):
        docs = provider.extract(["https://a.test", "https://b.test"])
        assert [d["url"] for d in docs] == ["https://a.test", "https://b.test"]
        assert all("KAGI_API_KEY" in d["error"] for d in docs)
        assert kagi_api.calls == []

    def test_http_failure_returns_per_url_error_dicts(self, provider, with_key, kagi_api):
        kagi_api.box["raise"] = httpx.HTTPError("boom")
        docs = provider.extract(["u"])
        assert all("Kagi extract failed" in d["error"] for d in docs)


class TestSetupSchema:
    def test_advertises_key_and_paid_badge(self, provider):
        schema = provider.get_setup_schema()
        assert schema["name"] == "Kagi"
        assert schema["badge"] == "paid"
        keys = [v["key"] for v in schema["env_vars"]]
        assert "KAGI_API_KEY" in keys
