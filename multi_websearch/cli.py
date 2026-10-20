from __future__ import annotations

import argparse
import json
import logging
import sys

from multi_websearch.config import load_settings
from multi_websearch.search import WebSearch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="multi-websearch",
        description="Pluggable multi-provider web search with ordered fallback",
    )
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument(
        "-n",
        "--max-results",
        type=int,
        default=None,
        help="Maximum number of results (default from config)",
    )
    parser.add_argument(
        "--providers",
        help="Comma-separated provider order override (e.g. tavily,brave,searxng)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit results as JSON",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show configured / active providers and exit",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    settings = load_settings()
    providers = None
    if args.providers:
        providers = [p.strip() for p in args.providers.split(",") if p.strip()]

    engine = WebSearch(settings=settings, providers=providers)

    if args.status:
        print(json.dumps(engine.status(), indent=2))
        return 0

    if not args.query:
        parser.error("query is required unless --status is used")

    results = engine.search(args.query, max_results=args.max_results)

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False))
    else:
        if not results:
            print("No results.", file=sys.stderr)
            return 1
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.title}")
            print(f"   {r.url}")
            if r.content:
                snippet = r.content.replace("\n", " ")[:200]
                print(f"   {snippet}")
            print(f"   [{r.provider}]")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
