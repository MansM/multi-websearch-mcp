"""Provider plugins. Importing this package registers the built-in providers."""

from multi_websearch.providers.base import SearchProvider, register, get_provider, list_providers
from multi_websearch.providers import ollama, tavily, brave, searxng  # noqa: F401 – side-effect registration

__all__ = [
    "SearchProvider",
    "register",
    "get_provider",
    "list_providers",
]
