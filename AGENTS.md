# AGENTS.md – multi-websearch

Guidance for AI coding agents working with this repository.

## Project purpose

`multi-websearch` is a small, dependency-light Python package that provides **ordered multi-provider web search with automatic fallback**.

It is designed to be used:

- as a library (`from multi_websearch import WebSearch`)
- via CLI (`multi-websearch`)
- as an HTTP service that implements the **Open WebUI external web-search API** (`POST /search`)

## Architecture (keep it)

```
multi_websearch/
  models.py          # SearchResult dataclass (title, url, content, provider)
  exceptions.py      # AuthError, RateLimitError, TemporaryError, ProviderError
  config.py          # pydantic-settings Settings (env + .env)
  search.py          # WebSearch orchestrator – ordered fallback
  cli.py             # CLI entry point
  server.py          # FastAPI Open WebUI-compatible endpoint
  providers/
    base.py          # SearchProvider ABC + registry (register / get_provider)
    ollama.py
    tavily.py
    brave.py
    searxng.py
```

### Core contract every provider must follow

```python
class SearchProvider(ABC):
    name: str
    def is_available(self) -> bool: ...
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]: ...
```

On failure a provider **must** raise one of:

| Exception        | Meaning                         | Orchestrator action |
|------------------|---------------------------------|---------------------|
| `AuthError`      | missing/invalid key             | skip, try next      |
| `RateLimitError` | 429 / quota / credits exhausted | skip, try next      |
| `TemporaryError` | timeout / 5xx / network         | skip, try next      |
| `ProviderError`  | other permanent-ish failure     | skip, try next      |

Never swallow errors inside a provider – let the orchestrator decide.

All providers return the **same** `SearchResult` shape so consumers (Open WebUI, OpenCode, agents) stay simple.

## Adding a new provider (plugin)

1. Create `multi_websearch/providers/<name>.py`.
2. Subclass `SearchProvider`, set `name = "<name>"`, implement `is_available` + `search`.
3. Decorate with `@register`.
4. Import the module in `providers/__init__.py` (side-effect registration).
5. Add any new env vars to `Settings` in `config.py` and document them in `.env.example` + README.
6. Users enable it by putting the name in `SEARCH_PROVIDERS`.

Do **not** hard-code the new provider into `WebSearch` – the registry is the only coupling point.

## Configuration rules

- API keys are **only** read from environment / `.env` via `Settings`.
- Never commit real keys.
- Missing key → provider is skipped at construction time (logged), not at search time.
- `SEARCH_PROVIDERS` is a comma-separated ordered list. First successful non-empty result wins.
- `SEARXNG_URL` + optional `SEARXNG_FALLBACK_URLS` – prefer self-hosted; public instances often disable JSON.

## Open WebUI contract (do not break)

```
POST /search
Authorization: Bearer <EXTERNAL_SEARCH_API_KEY>   # optional
{"query": str, "count": int}

Response: [{"link": str, "title": str, "snippet": str}, ...]
```

- On any internal error return `[]` (empty list), not 5xx, so Open WebUI stays stable.
- Auth is optional: only enforced when `EXTERNAL_SEARCH_API_KEY` is set.
- Keep `/health` and `/status` endpoints.

## Coding conventions

- Python ≥ 3.10, type hints, `from __future__ import annotations`.
- Prefer `httpx` over `requests`.
- No heavy frameworks inside providers (no LangChain, no official SDKs required).
- Keep the dependency surface minimal: `httpx`, `pydantic`, `pydantic-settings`, `fastapi`, `uvicorn`, `python-dotenv`.
- Logging via the `multi_websearch` logger; do not print in library code.

## Tests

- Unit tests live in `tests/`. Prefer tests that do **not** hit the network.
- When adding a provider, add at least a registration + `is_available` smoke test.
- Live integration tests (if any) must be clearly marked and skipped by default.

## What agents should NOT do

- Do not collapse the plugin system into a single if/elif file.
- Do not change the Open WebUI response field names (`link` / `title` / `snippet`).
- Do not make SearXNG require an API key.
- Do not add API keys to source or commit `.env`.
- Do not introduce breaking changes to `SearchResult` or the `WebSearch.search()` signature without a clear migration path.

## Docker

- `Dockerfile` – slim Python 3.12 image, non-root user, healthcheck on `/health`
- `docker-compose.yml` – single service + optional commented SearXNG
- `.dockerignore` – keeps the image small (no tests, caches, secrets)

Build/run:

```bash
docker compose up -d --build
# or
docker build -t multi-websearch . && docker run --rm -p 8018:8018 --env-file .env multi-websearch
```

Do not bake API keys into the image – always pass them via `--env-file` / compose `env_file` / runtime `-e`.

## Useful commands

```bash
pip install -e ".[dev]"
multi-websearch --status
multi-websearch "query" -n 5 --json
multi-websearch-server
pytest tests/ -v
docker compose up -d --build
```

## Extending for OpenCode / MCP

The same `WebSearch` class can power:

- an OpenCode custom tool / plugin (call `engine.search()` and format results)
- an MCP server exposing a `web_search` tool

Keep the core library free of OpenCode/MCP-specific code; put adapters in separate modules if needed.
