# multi-websearch

Pluggable multi-provider web search with **ordered fallback**.

Providers (plugins):

| Provider | Env key | Notes |
|----------|---------|-------|
| **ollama** | `OLLAMA_API_KEY` | Hosted Ollama web search (`https://ollama.com/api/web_search`) |
| **tavily** | `TAVILY_API_KEY` | Tavily Search API |
| **brave** | `BRAVE_API_KEY` or `BRAVE_SEARCH_API_KEY` | Brave Search API |
| **searxng** | none | SearXNG (self-hosted or public). Final fallback |

Order is configurable via `SEARCH_PROVIDERS` (default: `ollama,tavily,brave,searxng`).

On rate-limit / quota / auth / temporary errors the next provider is tried automatically.

---

## Install

```bash
cd multi-websearch
pip install -e .
# or
pip install -e ".[dev]"
```

Copy `.env.example` → `.env` and fill the keys you have.

---

## Docker

```bash
# 1. Configure secrets
cp .env.example .env
# edit .env – add the API keys you have

# 2. Build & run
docker compose up -d --build

# 3. Check
curl http://localhost:8000/health
curl http://localhost:8000/status
```

Plain Docker (no compose):

```bash
docker build -t multi-websearch .
docker run --rm -p 8000:8000 --env-file .env multi-websearch
```

Open WebUI → Admin → Web Search:

| Setting | Value |
|---------|-------|
| Engine | **external** |
| URL | `http://host.docker.internal:8000/search` (or the container name if same network) |
| API Key | value of `EXTERNAL_SEARCH_API_KEY` (or blank) |

To put multi-websearch on the same Docker network as Open WebUI, uncomment the `networks` sections in `docker-compose.yml` and set:

```
EXTERNAL_WEB_SEARCH_URL=http://multi-websearch:8000/search
```

An optional SearXNG service is commented in `docker-compose.yml` if you want a self-hosted fallback.

---

## Environment variables

```bash
# Required for the providers you want to use
OLLAMA_API_KEY=...
TAVILY_API_KEY=...
BRAVE_API_KEY=...          # or BRAVE_SEARCH_API_KEY

# Order (comma-separated)
SEARCH_PROVIDERS=ollama,tavily,brave,searxng

# SearXNG
SEARXNG_URL=https://searx.be/search
SEARXNG_FALLBACK_URLS=https://search.sapti.me/search,https://searx.tiekoetter.com/search

# Behaviour
SEARCH_MAX_RESULTS=5
SEARCH_TIMEOUT=15

# Open WebUI / HTTP server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
EXTERNAL_SEARCH_API_KEY=optional-secret   # if set, Open WebUI must send the same key
```

At startup the library logs which providers are active and which were skipped (missing key).

---

## Library usage

```python
from multi_websearch import WebSearch

engine = WebSearch()
results = engine.search("latest Python release", max_results=5)

for r in results:
    print(r.title, r.url, r.content[:80], r.provider)
```

Override order at runtime:

```python
engine = WebSearch(providers=["tavily", "brave", "searxng"])
```

---

## CLI

```bash
multi-websearch "what is ollama web search"
multi-websearch --json -n 3 "brave search api"
multi-websearch --status
multi-websearch --providers searxng,brave "test query" -v
```

---

## Open WebUI (external search engine)

1. Start the server:

```bash
# with keys already in the environment
multi-websearch-server
# or
uvicorn multi_websearch.server:app --host 0.0.0.0 --port 8000
```

2. In Open WebUI Admin → Settings → Web Search:

| Setting | Value |
|---------|-------|
| Enable Web Search | On |
| Web Search Engine | **external** |
| External Web Search URL | `http://<host>:8000/search` |
| External Web Search API Key | same value as `EXTERNAL_SEARCH_API_KEY` (or leave blank) |

3. The server implements the exact contract Open WebUI expects:

```
POST /search
{"query": "...", "count": 5}

→ [{"link": "...", "title": "...", "snippet": "..."}, ...]
```

Health / diagnostics:

- `GET /health`
- `GET /status`

---

## Adding a new provider (plugin)

1. Create `multi_websearch/providers/myprovider.py`:

```python
from multi_websearch.providers.base import SearchProvider, register
from multi_websearch.models import SearchResult
from multi_websearch.exceptions import AuthError, RateLimitError, TemporaryError

@register
class MyProvider(SearchProvider):
    name = "myprovider"

    def is_available(self) -> bool:
        return bool(self.settings.my_api_key)  # add to Settings

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        # raise AuthError / RateLimitError / TemporaryError on failure
        ...
```

2. Import it in `providers/__init__.py` so registration runs.

3. Add the name to `SEARCH_PROVIDERS`.

---

## Design notes

- Every provider returns the same `SearchResult` dataclass → easy consumption by OpenCode tools, Open WebUI, or any agent.
- Failures that should trigger fallback (`RateLimitError`, `AuthError`, `TemporaryError`) are explicit.
- SearXNG is always available as a no-key last resort; public instances are flaky, so a self-hosted URL is strongly recommended.
- The package is intentionally dependency-light (`httpx` + `fastapi`/`uvicorn` only).
