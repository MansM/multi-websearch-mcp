"""Minimal smoke tests (no live network calls)."""

from multi_websearch.config import Settings
from multi_websearch.models import SearchResult
from multi_websearch.providers.base import list_providers
from multi_websearch.search import WebSearch


def test_plugins_registered():
    names = list_providers()
    assert "ollama" in names
    assert "tavily" in names
    assert "brave" in names
    assert "searxng" in names


def test_search_result_openwebui_shape():
    r = SearchResult(title="T", url="https://example.com", content="S", provider="test")
    ow = r.to_openwebui()
    assert ow == {"link": "https://example.com", "title": "T", "snippet": "S"}


def test_engine_status_with_no_keys(monkeypatch):
    # Ensure no keys are present
    for k in ("OLLAMA_API_KEY", "TAVILY_API_KEY", "BRAVE_API_KEY", "BRAVE_SEARCH_API_KEY"):
        monkeypatch.delenv(k, raising=False)

    settings = Settings(
        search_providers="ollama,tavily,brave,searxng",
        ollama_api_key=None,
        tavily_api_key=None,
        brave_api_key=None,
        searxng_url="https://example.invalid/search",
    )
    engine = WebSearch(settings=settings)
    status = engine.status()
    # Only searxng should be active (no key required)
    assert status["active"] == ["searxng"]
    assert "ollama" in status["skipped"]
    assert "tavily" in status["skipped"]
    assert "brave" in status["skipped"]
