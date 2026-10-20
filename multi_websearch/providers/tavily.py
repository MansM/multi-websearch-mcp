from __future__ import annotations

import httpx

from multi_websearch.config import Settings, load_settings
from multi_websearch.exceptions import AuthError, ProviderError, RateLimitError, TemporaryError
from multi_websearch.models import SearchResult
from multi_websearch.providers.base import SearchProvider, register


@register
class TavilyProvider(SearchProvider):
    """Tavily Search API (https://api.tavily.com/search)."""

    name = "tavily"
    ENDPOINT = "https://api.tavily.com/search"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.api_key = self.settings.tavily_api_key
        self.timeout = self.settings.request_timeout

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not self.api_key:
            raise AuthError(self.name, "TAVILY_API_KEY not set")

        headers = {
            "Content-Type": "application/json",
        }
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
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
            # Tavily sometimes returns 400 with quota messages
            text = resp.text.lower()
            if any(k in text for k in ("quota", "limit", "rate", "exceeded", "credits")):
                raise RateLimitError(self.name, f"HTTP {resp.status_code}: {resp.text[:200]}")
            raise ProviderError(self.name, f"HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        results_raw = data.get("results") or []
        out: list[SearchResult] = []
        for item in results_raw[:max_results]:
            out.append(
                SearchResult(
                    title=item.get("title") or "",
                    url=item.get("url") or "",
                    content=item.get("content") or item.get("snippet") or "",
                    provider=self.name,
                    score=item.get("score"),
                )
            )
        return out
