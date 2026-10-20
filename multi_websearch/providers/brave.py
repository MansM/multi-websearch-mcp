from __future__ import annotations

import httpx

from multi_websearch.config import Settings, load_settings
from multi_websearch.exceptions import AuthError, ProviderError, RateLimitError, TemporaryError
from multi_websearch.models import SearchResult
from multi_websearch.providers.base import SearchProvider, register


@register
class BraveProvider(SearchProvider):
    """Brave Search API (https://api.search.brave.com/res/v1/web/search)."""

    name = "brave"
    ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.api_key = self.settings.brave_api_key
        self.timeout = self.settings.request_timeout

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not self.api_key:
            raise AuthError(self.name, "BRAVE_API_KEY / BRAVE_SEARCH_API_KEY not set")

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        params = {
            "q": query,
            "count": min(max_results, 20),
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(self.ENDPOINT, headers=headers, params=params)
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
            text = resp.text.lower()
            if any(k in text for k in ("quota", "limit", "rate", "exceeded")):
                raise RateLimitError(self.name, f"HTTP {resp.status_code}: {resp.text[:200]}")
            raise ProviderError(self.name, f"HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        web = data.get("web") or {}
        results_raw = web.get("results") or []
        out: list[SearchResult] = []
        for item in results_raw[:max_results]:
            out.append(
                SearchResult(
                    title=item.get("title") or "",
                    url=item.get("url") or "",
                    content=item.get("description") or item.get("extra_snippets", [""])[0]
                    if item.get("extra_snippets")
                    else item.get("description") or "",
                    provider=self.name,
                )
            )
        return out
