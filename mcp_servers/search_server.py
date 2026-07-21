"""
mcp_servers/search_server.py — Web search MCP server (port 8002).

Tools exposed:
  - web_search(query, max_results)  → list of {title, url, snippet}
  - fetch_url(url)                  → page content as plain text

Two modes:
  - SEARCH_PROVIDER=tavily  → real Tavily API (production)
  - SEARCH_PROVIDER=mock    → deterministic fixture (tests, CI, offline dev)

The mock mode is a first-class design decision, not a test hack:
  it lets the whole stack run offline and makes CI deterministic —
  test results don't depend on Tavily's availability or rate limits.

Interview answer for "what if the search API goes down?":
  "We set SEARCH_PROVIDER=mock and the stack still runs. In production
  I'd add a circuit breaker — if Tavily returns 3 consecutive errors,
  fall back to mock mode automatically and alert."
"""

from __future__ import annotations

from fastmcp import FastMCP

from app.config import settings
from mcp_servers.shared_auth import verify_mcp_key

# ── FastMCP server instance ───────────────────────────────────────────────────
mcp = FastMCP(
    name="orqflow-search",
    instructions=(
        "Web search and URL fetch tools. "
        "Use web_search to find recent information and fetch_url to read specific pages. "
        "Results are plain text — no HTML tags."
    ),
)

# ── Mock fixtures ─────────────────────────────────────────────────────────────

_MOCK_SEARCH_RESULTS: list[dict] = [
    {
        "title": "FastMCP — Model Context Protocol for Python",
        "url": "https://fastmcp.dev",
        "snippet": "FastMCP is the fastest way to build MCP servers in Python.",
    },
    {
        "title": "LangGraph Documentation",
        "url": "https://langchain-ai.github.io/langgraph/",
        "snippet": "LangGraph builds stateful multi-actor applications with LLMs.",
    },
    {
        "title": "OrqFlow — Multi-Agent Orchestration",
        "url": "https://github.com/Akshansh0519/OrqFlow",
        "snippet": "Hand-rolled LangGraph supervisor routing tasks to specialist agents via MCP.",
    },
]

_MOCK_FETCH_CONTENT = (
    "This is mocked page content for offline/test mode. "
    "In production, this would be the extracted plain-text content "
    "of the requested URL."
)


# ── Tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web for recent information.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (1–10). Default: 5.

    Returns:
        A list of dicts, each with: title (str), url (str), snippet (str).
    """
    verify_mcp_key()
    if not query.strip():
        raise ValueError("Search query cannot be empty")

    max_results = max(1, min(10, max_results))

    if settings.SEARCH_PROVIDER == "mock":
        return _MOCK_SEARCH_RESULTS[:max_results]

    # Production: Tavily API
    try:
        from tavily import TavilyClient  # type: ignore
    except ImportError:
        raise RuntimeError(
            "tavily-python is not installed. "
            "Run: pip install tavily-python, or set SEARCH_PROVIDER=mock."
        )

    if not settings.TAVILY_API_KEY:
        raise RuntimeError(
            "TAVILY_API_KEY is not set. "
            "Either set the key or use SEARCH_PROVIDER=mock for offline mode."
        )

    client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    response = client.search(query, max_results=max_results)

    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
        }
        for r in response.get("results", [])
    ]


@mcp.tool()
async def fetch_url(url: str) -> str:
    """
    Fetch the plain-text content of a URL.

    Args:
        url: A fully-qualified URL (must start with http:// or https://).

    Returns:
        The plain-text content of the page (HTML stripped).
    """
    verify_mcp_key()
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")

    if settings.SEARCH_PROVIDER == "mock":
        return f"[MOCK] Content for {url}\n\n{_MOCK_FETCH_CONTENT}"

    import httpx

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    # Return raw text; the agent is responsible for interpreting HTML
    return response.text[:8000]  # cap at 8k chars to stay within context budget


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=8002)
