"""Provider plugins. Importing this package registers the built-in providers."""

from multi_websearch.providers import (  # noqa: F401 – side-effect registration
    brave,
    ollama,
    searxng,
    tavily,
)
from multi_websearch.providers.base import SearchProvider, get_provider, list_providers, register

__all__ = [
    "SearchProvider",
    "get_provider",
    "list_providers",
    "register",
]
