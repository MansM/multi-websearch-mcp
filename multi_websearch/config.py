from __future__ import annotations

import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables (and optional .env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Ordered list of provider names. First available & successful wins.
    # Example: "ollama,tavily,brave,searxng"
    search_providers: str = Field(
        default="ollama,tavily,brave,searxng",
        validation_alias="SEARCH_PROVIDERS",
    )

    # --- Provider API keys (optional; missing key → provider skipped) ---
    ollama_api_key: str | None = Field(default=None, validation_alias="OLLAMA_API_KEY")
    tavily_api_key: str | None = Field(default=None, validation_alias="TAVILY_API_KEY")
    brave_api_key: str | None = Field(
        default=None, validation_alias="BRAVE_API_KEY"
    )  # also accept BRAVE_SEARCH_API_KEY

    # --- SearXNG (no key required) ---
    searxng_url: str = Field(
        default="https://searx.be/search",
        validation_alias="SEARXNG_URL",
    )
    # Comma-separated fallback instances tried in order if the primary fails
    searxng_fallback_urls: str = Field(
        default="",
        validation_alias="SEARXNG_FALLBACK_URLS",
    )

    # --- Behaviour ---
    default_max_results: int = Field(default=5, validation_alias="SEARCH_MAX_RESULTS")
    request_timeout: float = Field(default=15.0, validation_alias="SEARCH_TIMEOUT")

    # --- Open WebUI / HTTP server ---
    server_host: str = Field(default="0.0.0.0", validation_alias="SERVER_HOST")
    server_port: int = Field(default=8018, validation_alias="SERVER_PORT")
    # Optional bearer token that Open WebUI must send as EXTERNAL_WEB_SEARCH_API_KEY
    external_api_key: str | None = Field(
        default=None, validation_alias="EXTERNAL_SEARCH_API_KEY"
    )

    def provider_order(self) -> List[str]:
        return [p.strip().lower() for p in self.search_providers.split(",") if p.strip()]

    def searxng_urls(self) -> List[str]:
        urls = [self.searxng_url.strip()]
        if self.searxng_fallback_urls:
            urls.extend(
                u.strip() for u in self.searxng_fallback_urls.split(",") if u.strip()
            )
        # de-dupe while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)
        return unique


def load_settings() -> Settings:
    """Load settings; also accept the alternate Brave env name."""
    # Allow BRAVE_SEARCH_API_KEY as alias
    if not os.getenv("BRAVE_API_KEY") and os.getenv("BRAVE_SEARCH_API_KEY"):
        os.environ["BRAVE_API_KEY"] = os.environ["BRAVE_SEARCH_API_KEY"]
    return Settings()
