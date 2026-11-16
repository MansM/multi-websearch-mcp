# multi-websearch – Open WebUI external search endpoint
# Build:  docker build -t multi-websearch .
# Run:    docker run --rm -p 8018:8018 --env-file .env multi-websearch

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps (ca-certificates for HTTPS to search APIs)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

# Install package
COPY pyproject.toml README.md ./
COPY multi_websearch ./multi_websearch
RUN pip install --no-cache-dir .

# Non-root user (Debian slim has no bash by default)
RUN useradd --create-home --shell /bin/sh appuser
USER appuser

EXPOSE 8018

# Defaults – override with -e / --env-file
ENV SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8018 \
    SEARCH_PROVIDERS=ollama,tavily,brave,searxng \
    SEARCH_MAX_RESULTS=5 \
    SEARCH_TIMEOUT=15

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8018/health')" || exit 1

CMD ["python", "-m", "multi_websearch.server"]
