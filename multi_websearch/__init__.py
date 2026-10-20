"""multi-websearch: pluggable multi-provider web search with ordered fallback."""

from multi_websearch.models import SearchResult
from multi_websearch.search import WebSearch
from multi_websearch.config import Settings

__all__ = ["SearchResult", "WebSearch", "Settings"]
__version__ = "0.1.0"
