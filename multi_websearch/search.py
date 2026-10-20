from __future__ import annotations

import logging
from typing import Sequence

from multi_websearch.config import Settings, load_settings
from multi_websearch.exceptions import AuthError, ProviderError, RateLimitError, TemporaryError
from multi_websearch.models import SearchResult
from multi_websearch.providers import get_provider, list_providers
from multi_websearch.providers.base import SearchProvider

logger = logging.getLogger("multi_websearch")


class WebSearch:
    """
    Ordered multi-provider search orchestrator.

    Providers are tried in the order given by Settings.search_providers.
    A provider is skipped when:
      - it is not available (missing key)
      - it raises AuthError / RateLimitError / TemporaryError / ProviderError

    The first provider that returns a non-empty result list wins.
    If every provider fails or returns empty, an empty list is returned
    (or the last exception is re-raised if raise_on_empty=True).
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        providers: Sequence[str] | None = None,
        raise_on_empty: bool = False,
    ):
        self.settings = settings or load_settings()
        self.raise_on_empty = raise_on_empty
        order = list(providers) if providers is not None else self.settings.provider_order()
        self._providers: list[SearchProvider] = []
        self._skipped: list[str] = []

        for name in order:
            try:
                p = get_provider(name, settings=self.settings)
            except KeyError:
                logger.warning("Unknown provider %r – skipping", name)
                self._skipped.append(name)
                continue
            if not p.is_available():
                logger.info("Provider %r not available (missing key / config) – skipping", name)
                self._skipped.append(name)
                continue
            self._providers.append(p)

        if not self._providers:
            logger.warning(
                "No usable search providers. Configured order=%s, available plugins=%s",
                order,
                list_providers(),
            )

    @property
    def active_providers(self) -> list[str]:
        return [p.name for p in self._providers]

    @property
    def skipped_providers(self) -> list[str]:
        return list(self._skipped)

    def search(self, query: str, max_results: int | None = None) -> list[SearchResult]:
        if not query or not query.strip():
            return []

        limit = max_results if max_results is not None else self.settings.default_max_results
        last_error: Exception | None = None

        for provider in self._providers:
            try:
                results = provider.search(query.strip(), max_results=limit)
                if results:
                    logger.debug(
                        "Provider %s returned %d results for %r",
                        provider.name,
                        len(results),
                        query[:60],
                    )
                    return results
                logger.info("Provider %s returned empty results – trying next", provider.name)
            except AuthError as e:
                logger.warning("Auth error from %s: %s – skipping", e.provider, e.message)
                last_error = e
            except RateLimitError as e:
                logger.warning("Rate/quota limit from %s: %s – falling back", e.provider, e.message)
                last_error = e
            except TemporaryError as e:
                logger.warning("Temporary error from %s: %s – falling back", e.provider, e.message)
                last_error = e
            except ProviderError as e:
                logger.warning("Provider error from %s: %s – falling back", e.provider, e.message)
                last_error = e
            except Exception as e:
                logger.exception("Unexpected error from %s – falling back", provider.name)
                last_error = e

        if self.raise_on_empty and last_error:
            raise last_error
        return []

    def status(self) -> dict:
        """Return a diagnostic snapshot useful at startup."""
        return {
            "configured_order": self.settings.provider_order(),
            "active": self.active_providers,
            "skipped": self.skipped_providers,
            "known_plugins": list_providers(),
        }
