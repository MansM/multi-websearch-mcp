"""
FastAPI server implementing the Open WebUI *external* web-search contract.

Open WebUI configuration:
  WEB_SEARCH_ENGINE=external
  EXTERNAL_WEB_SEARCH_URL=http://<host>:<port>/search
  EXTERNAL_WEB_SEARCH_API_KEY=<same value as EXTERNAL_SEARCH_API_KEY env, or leave blank>

MCP configuration (OpenCode / Open WebUI native MCP):
  URL: http://<host>:<port>/mcp

Request (Open WebUI external search):
  POST /search
  Authorization: Bearer <key>   (optional)
  {"query": "...", "count": 5}

Response:
  [
    {"link": "...", "title": "...", "snippet": "..."},
    ...
  ]
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from multi_websearch.config import load_settings
from multi_websearch.search import WebSearch

logger = logging.getLogger("multi_websearch.server")

settings = load_settings()
engine = WebSearch(settings=settings)

# ---------------------------------------------------------------------------
# MCP server (Streamable HTTP – works with OpenCode remote and Open WebUI MCP)
# ---------------------------------------------------------------------------

mcp = FastMCP("multi-websearch")


@mcp.tool()
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web using multiple providers with automatic fallback."""
    results = engine.search(query, max_results=max_results)
    if not results:
        return "No results found."
    blocks = []
    for res in results:
        blocks.append(
            f"Title: {res.title}\nURL: {res.url}\nContent: {res.content}\nProvider: {res.provider}\n"
        )
    return "\n\n".join(blocks)


@mcp.tool()
def get_status() -> str:
    """Get the current operational status of the search engine."""
    return json.dumps(engine.status(), indent=2)


mcp_app = mcp.http_app(transport="streamable-http", path="/", stateless_http=True)

# ---------------------------------------------------------------------------
# FastAPI app – mounts MCP at /mcp and exposes the Open WebUI /search endpoint
# ---------------------------------------------------------------------------

app = FastAPI(
    title="multi-websearch",
    description=(
        "Multi-provider web search (Ollama / Tavily / Brave / SearXNG) with fallback. "
        "Implements the Open WebUI external search contract (POST /search) "
        "and MCP Streamable HTTP (/mcp) for OpenCode and Open WebUI native MCP."
    ),
    version="0.1.0",
    lifespan=mcp_app.lifespan,
)

# MCP Streamable HTTP endpoint
app.mount("/mcp", mcp_app)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    count: int = Field(default=5, ge=1, le=50)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "providers": engine.status(),
    }


@app.get("/status")
def status() -> dict[str, Any]:
    return engine.status()


@app.post("/search")
def search(
    body: SearchRequest,
    authorization: str | None = Header(default=None),
) -> list[dict[str, str]]:
    """Open WebUI external web-search endpoint."""
    expected = settings.external_api_key
    if expected:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
        token = authorization[len("Bearer "):].strip()
        if token != expected:
            raise HTTPException(status_code=401, detail="Invalid API key")

    try:
        results = engine.search(body.query, max_results=body.count)
    except Exception:
        logger.exception("Search failed")
        # Open WebUI expects an empty list on error rather than a 5xx
        return []

    return [r.to_openwebui() for r in results]


def main() -> None:
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Starting multi-websearch server – active providers: %s", engine.active_providers)
    if engine.skipped_providers:
        logger.warning("Skipped providers (missing key/config): %s", engine.skipped_providers)

    uvicorn.run(
        "multi_websearch.server:app",
        host=settings.server_host,
        port=settings.server_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
