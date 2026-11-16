"""multi-websearch: pluggable multi-provider web search with ordered fallback."""

from multi_websearch.config import Settings
from multi_websearch.models import SearchResult
from multi_websearch.search import WebSearch

__all__ = ["SearchResult", "Settings", "WebSearch"]
__version__ = "0.1.0"
