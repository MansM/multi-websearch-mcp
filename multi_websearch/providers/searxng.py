from __future__ import annotations

import httpx

from multi_websearch.config import Settings, load_settings
from multi_websearch.exceptions import ProviderError, RateLimitError, TemporaryError
from multi_websearch.models import SearchResult
from multi_websearch.providers.base import SearchProvider, register


@register
class SearXNGProvider(SearchProvider):
    """
    SearXNG metasearch (no API key required).

    Tries the primary SEARXNG_URL and any SEARXNG_FALLBACK_URLS in order.
    Public instances often disable JSON or rate-limit; prefer a self-hosted instance.
    """

    name = "searxng"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.urls = self.settings.searxng_urls()
        self.timeout = self.settings.request_timeout

    def is_available(self) -> bool:
        return bool(self.urls)

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        last_error: Exception | None = None

        for base_url in self.urls:
            try:
                return self._search_one(base_url, query, max_results)
            except (RateLimitError, TemporaryError, ProviderError) as e:
                last_error = e
                continue

        if last_error:
            raise last_error
        raise ProviderError(self.name, "no SearXNG URLs configured")

    def _search_one(self, base_url: str, query: str, max_results: int) -> list[SearchResult]:
        # Accept either a full /search URL or a base instance URL
        url = base_url.rstrip("/")
        if not url.endswith("/search"):
            url = f"{url}/search"

        params = {
            "q": query,
            "format": "json",
            "pageno": 1,
        }

        headers = {
            "User-Agent": "multi-websearch/0.1 (https://github.com/)",
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as e:
            raise TemporaryError(self.name, f"timeout contacting {url}: {e}") from e
        except httpx.RequestError as e:
            raise TemporaryError(self.name, f"network error contacting {url}: {e}") from e

        if resp.status_code == 429:
            raise RateLimitError(self.name, f"HTTP 429 from {url}")
        if resp.status_code == 403:
            # Common when JSON format is disabled on public instances
            raise ProviderError(
                self.name,
                f"HTTP 403 from {url} – JSON format may be disabled on this instance",
            )
        if resp.status_code >= 500:
            raise TemporaryError(self.name, f"HTTP {resp.status_code} from {url}")
        if resp.status_code != 200:
            raise ProviderError(self.name, f"HTTP {resp.status_code} from {url}: {resp.text[:200]}")

        try:
            data = resp.json()
        except Exception as e:
            raise ProviderError(self.name, f"invalid JSON from {url}: {e}") from e

        results_raw = data.get("results") or []
        out: list[SearchResult] = []
        for item in results_raw[:max_results]:
            out.append(
                SearchResult(
                    title=item.get("title") or "",
                    url=item.get("url") or "",
                    content=item.get("content") or item.get("snippet") or "",
                    provider=self.name,
                )
            )
        return out
