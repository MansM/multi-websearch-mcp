from __future__ import annotations

import httpx

from multi_websearch.config import Settings, load_settings
from multi_websearch.exceptions import AuthError, ProviderError, RateLimitError, TemporaryError
from multi_websearch.models import SearchResult
from multi_websearch.providers.base import SearchProvider, register


@register
class OllamaProvider(SearchProvider):
    """Ollama hosted web search (https://ollama.com/api/web_search)."""

    name = "ollama"
    ENDPOINT = "https://ollama.com/api/web_search"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.api_key = self.settings.ollama_api_key
        self.timeout = self.settings.request_timeout

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not self.api_key:
            raise AuthError(self.name, "OLLAMA_API_KEY not set")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "max_results": min(max_results, 10),
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.ENDPOINT, headers=headers, json=payload)
        except httpx.TimeoutException as e:
            raise TemporaryError(self.name, f"timeout: {e}") from e
        except httpx.RequestError as e:
            raise TemporaryError(self.name, f"network error: {e}") from e

        if resp.status_code in (401, 403):
            raise AuthError(self.name, f"HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code == 429:
            raise RateLimitError(self.name, f"HTTP 429: {resp.text[:200]}")
        if resp.status_code >= 500:
            raise TemporaryError(self.name, f"HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code != 200:
            raise ProviderError(self.name, f"HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        results_raw = data.get("results") or []
        out: list[SearchResult] = []
        for item in results_raw[:max_results]:
            out.append(
                SearchResult(
                    title=item.get("title") or "",
                    url=item.get("url") or "",
                    content=item.get("content") or "",
                    provider=self.name,
                )
            )
        return out
