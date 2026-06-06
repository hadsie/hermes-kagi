"""Tests for the shared Kagi API client (client.py)."""

from __future__ import annotations

import httpx
import pytest

from web_kagi import client


class TestKagiBaseUrl:
    def test_defaults_to_kagi_api_root(self):
        assert client.kagi_base_url() == "https://kagi.com/api"

    def test_honors_override_and_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("KAGI_BASE_URL", "https://proxy.local/kagi/")
        assert client.kagi_base_url() == "https://proxy.local/kagi"


class TestKagiHeaders:
    def test_raises_when_key_missing(self):
        with pytest.raises(ValueError, match="KAGI_API_KEY"):
            client.kagi_headers()

    def test_raises_when_key_blank(self, monkeypatch):
        monkeypatch.setenv("KAGI_API_KEY", "   ")
        with pytest.raises(ValueError, match="KAGI_API_KEY"):
            client.kagi_headers()

    def test_returns_bearer_header_when_key_present(self, with_key):
        assert client.kagi_headers() == {"Authorization": "Bearer test-key-123"}


class TestKagiPost:
    def test_builds_versioned_url_and_sends_body(self, with_key, kagi_api):
        client.kagi_post("search", {"query": "rust"})
        call = kagi_api.calls[-1]
        assert call["url"] == "https://kagi.com/api/v1/search"
        assert call["json"] == {"query": "rust"}
        assert call["headers"] == {"Authorization": "Bearer test-key-123"}

    def test_strips_leading_slash_from_endpoint(self, with_key, kagi_api):
        client.kagi_post("/extract", {"pages": []})
        assert kagi_api.calls[-1]["url"] == "https://kagi.com/api/v1/extract"

    def test_forwards_timeout(self, with_key, kagi_api):
        client.kagi_post("extract", {"pages": []}, timeout=120)
        assert kagi_api.calls[-1]["timeout"] == 120

    def test_returns_parsed_json(self, with_key, kagi_api):
        kagi_api.box["search"] = {"data": {"search": [{"title": "x"}]}}
        assert client.kagi_post("search", {"query": "x"}) == kagi_api.box["search"]

    def test_raises_without_key_before_network(self, kagi_api):
        with pytest.raises(ValueError, match="KAGI_API_KEY"):
            client.kagi_post("search", {"query": "x"})
        assert kagi_api.calls == []

    def test_propagates_http_errors(self, with_key, kagi_api):
        kagi_api.box["raise"] = httpx.HTTPError("boom")
        with pytest.raises(httpx.HTTPError):
            client.kagi_post("search", {"query": "x"})


class TestBuildSearchBody:
    def test_query_only_body(self):
        assert client.build_search_body("rust") == {"query": "rust"}

    def test_truthy_fields_are_included(self):
        body = client.build_search_body("rust", limit=10, lens_id="programming")
        assert body == {"query": "rust", "limit": 10, "lens_id": "programming"}

    def test_falsy_fields_are_dropped(self):
        body = client.build_search_body("rust", limit=None, filters={}, lens_id="")
        assert body == {"query": "rust"}

    def test_nested_filters_passthrough(self):
        body = client.build_search_body("rust", filters={"after": "2026-01-01"})
        assert body["filters"] == {"after": "2026-01-01"}

    def test_safe_search_disabled_when_env_off(self, monkeypatch):
        monkeypatch.setenv("KAGI_SAFE_SEARCH", "OFF")
        assert client.build_search_body("rust")["safe_search"] is False

    def test_safe_search_omitted_by_default(self):
        assert "safe_search" not in client.build_search_body("rust")

    def test_other_safe_search_values_ignored(self, monkeypatch):
        monkeypatch.setenv("KAGI_SAFE_SEARCH", "false")
        assert "safe_search" not in client.build_search_body("rust")


class TestNormalizeSearchResults:
    def test_maps_search_array_to_web_entries(self):
        response = {
            "data": {
                "search": [
                    {"title": "First", "url": "https://a.test", "snippet": "alpha"},
                    {"title": "Second", "url": "https://b.test", "snippet": "beta"},
                ]
            }
        }
        result = client.normalize_kagi_search_results(response)
        assert result == {
            "success": True,
            "data": {
                "web": [
                    {"title": "First", "url": "https://a.test", "description": "alpha", "position": 1},
                    {"title": "Second", "url": "https://b.test", "description": "beta", "position": 2},
                ]
            },
        }

    def test_missing_fields_become_empty_strings(self):
        response = {"data": {"search": [{}]}}
        web = client.normalize_kagi_search_results(response)["data"]["web"]
        assert web == [{"title": "", "url": "", "description": "", "position": 1}]

    def test_empty_or_missing_data_yields_no_web_results(self):
        assert client.normalize_kagi_search_results({})["data"]["web"] == []
        assert client.normalize_kagi_search_results({"data": {}})["data"]["web"] == []
        assert client.normalize_kagi_search_results({"data": {"search": []}})["data"]["web"] == []

    def test_non_dict_items_are_skipped_keeping_original_position(self):
        response = {"data": {"search": [{"title": "ok", "url": "u"}, "garbage", {"title": "two"}]}}
        web = client.normalize_kagi_search_results(response)["data"]["web"]
        assert [w["title"] for w in web] == ["ok", "two"]
        # position reflects the original index, so the skipped item leaves a gap.
        assert [w["position"] for w in web] == [1, 3]
