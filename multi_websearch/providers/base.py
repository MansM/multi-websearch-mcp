from __future__ import annotations

from abc import ABC, abstractmethod

from multi_websearch.models import SearchResult


class SearchProvider(ABC):
    """Abstract base class every search plugin must implement."""

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the provider can be used (key present, etc.)."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """
        Execute a search.

        Must raise one of:
          - AuthError
          - RateLimitError
          - TemporaryError
          - ProviderError
        on failure so the orchestrator can decide whether to fall back.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} available={self.is_available()}>"


# ---------------------------------------------------------------------------
# Simple plugin registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, type[SearchProvider]] = {}


def register(cls: type[SearchProvider]) -> type[SearchProvider]:
    """Decorator / helper to register a provider class by its `.name`."""
    if not getattr(cls, "name", None):
        raise ValueError(f"{cls} must define a class attribute `name`")
    _REGISTRY[cls.name.lower()] = cls
    return cls


def get_provider(name: str, **kwargs) -> SearchProvider:
    key = name.lower()
    if key not in _REGISTRY:
        raise KeyError(
            f"Unknown provider {name!r}. Available: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[key](**kwargs)


def list_providers() -> list[str]:
    return sorted(_REGISTRY.keys())
