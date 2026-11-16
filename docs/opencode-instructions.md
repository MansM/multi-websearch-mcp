# Web search: use the multi-websearch MCP server

The `multi-websearch` service exposes web search as an **MCP server**
(remote, streamable HTTP — by default `http://localhost:8018/mcp`).
It performs ordered multi-provider search with automatic fallback
(ollama → tavily → brave → searxng, configurable via `SEARCH_PROVIDERS`).

Once the server is registered in OpenCode (as `websearch`, or another name of
your choosing), these tools are available:

| Tool         | Purpose                                                                    |
|--------------|----------------------------------------------------------------------------|
| `search_web` | Live web search. Args: `query` (required), `max_results` (optional, 1–10) |
| `get_status` | Report which providers are configured, active and skipped                  |

## Rules for agents

1. Prefer these tools for any live web search instead of ad-hoc HTTP scraping.
2. **How you call them depends on how they are exposed:**
   - If they are listed under **Code Mode tools**, they must be called as
     JavaScript inside the `execute` tool, never as direct tool calls:

     ```js
     // inside execute ("websearch" = the server name in the OpenCode config)
     return await tools.websearch.search_web({ query: "…", max_results: 5 })
     return await tools.websearch.get_status()
     ```

   - If they appear as regular tools in your tool list, call them directly.
   - A wrong-style call fails **silently**: the call leaks into the output as
     raw `tool_call`/`<function=…>` XML text and never executes. If you see
     that in your own output, stop and switch to the other calling form.
3. If `search_web` fails, call `get_status` to see the provider state, then
   report the problem — do not hunt for a different search tool.
4. Never try to call OpenCode's built-in `websearch` tool when the config
   disables it (`"tools": { "websearch": false }`); use this MCP server instead.
5. `webfetch` is unaffected and remains the right tool for reading a known URL.

## If the server appears unreachable

- Start it: `docker compose up -d` in a clone of
  [MansM/multi-websearch-mcp](https://github.com/MansM/multi-websearch-mcp)
  (or `pip install multi-websearch` and run `multi-websearch-server`).
  The MCP endpoint lives at `/mcp` on `SERVER_PORT` (default **8018**).
- Check it: `curl http://localhost:8018/health`
- After the container is rebuilt or restarted, OpenCode may hold a dead MCP
  session — `opencode mcp list` can still report "connected" while calls fail.
  Fix: toggle the server's `enabled` to `false` and back to `true` in
  `opencode.json`; the config hot-reload reconnects it. Verify with
  `get_status`.
