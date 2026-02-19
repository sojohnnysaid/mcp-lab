"""
MCP Server — Enterprise Search Tool
Uses FastMCP (official Python SDK) with stdio transport.

Exposes a single tool: kb_search(query, top_k)
Calls the mock enterprise search API endpoint.
"""

from mcp.server.fastmcp import FastMCP
import httpx
import sys
import json
import os

# ---------------------------------------------------------------------------
# Configuration — point to the mock search API
# Local:  http://localhost:8080  (mock_search_api.py)
# Lambda: https://<id>.lambda-url.<region>.on.aws
# ---------------------------------------------------------------------------
ENDPOINT = os.environ.get(
    "SEARCH_ENDPOINT",
    "http://localhost:8080",
)

mcp = FastMCP("enterprise-search")


@mcp.tool()
async def kb_search(query: str, top_k: int = 3) -> str:
    """Search the enterprise knowledge base.

    Returns ranked results with titles, snippets, relevance scores,
    and permission groups (acl_group). Use this tool to find authoritative
    enterprise documents before answering questions.

    Args:
        query: Natural language search query
        top_k: Maximum number of results to return (default 3)
    """
    url = f"{ENDPOINT}/search?q={query}&top_k={top_k}"

    # Log to stderr, NEVER stdout (stdout = JSON-RPC transport)
    print(f"[kb_search] Calling: {url}", file=sys.stderr)

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()

    data = resp.json()
    print(f"[kb_search] Got {len(data.get('results', []))} results", file=sys.stderr)

    return json.dumps(data, indent=2)


if __name__ == "__main__":
    print("[server] Starting MCP server (stdio transport)...", file=sys.stderr)
    mcp.run(transport="stdio")
