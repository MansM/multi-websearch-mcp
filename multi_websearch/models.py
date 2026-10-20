from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(slots=True)
class SearchResult:
    """Normalized search result used by every provider."""

    title: str
    url: str
    content: str  # snippet / content
    provider: str = ""
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_openwebui(self) -> dict[str, str]:
        """Shape expected by Open WebUI external search API."""
        return {
            "link": self.url,
            "title": self.title or "",
            "snippet": self.content or "",
        }
