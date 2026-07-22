"""
app/graph/tools.py — Tool loading for specialist agents.

Two modes:

  MOCK MODE (SEARCH_PROVIDER=mock or use_mock=True):
    Imports tool functions directly from mcp_servers Python modules and wraps
    them as LangChain tools. No HTTP, no running MCP servers needed.
    This is the test/offline/CI path.

  PRODUCTION MODE:
    Uses langchain_mcp_adapters.MultiServerMCPClient to discover and load tools
    from the 3 HTTP MCP servers (mcp-db:8001, mcp-search:8002, mcp-files:8003).
    Tools are returned as a list of LangChain BaseTool objects.

Tool assignment per specialist:
  researcher  → web_search, fetch_url
  analyst     → query_database, list_tables, describe_table
  coder       → read_file, write_file, list_files, lint_python

interview_answer: "Why not give every agent all tools?"
  "Separation of concerns and least-privilege. The analyst has no reason to
  touch the filesystem; the researcher has no reason to query the database.
  Giving each agent only the tools it needs makes the system auditable,
  reduces attack surface, and makes tool call traces easier to read."
"""

from __future__ import annotations

import structlog
from langchain_core.tools import tool as lc_tool

from app.config import settings

logger = structlog.get_logger()


# ── Mock tool wrappers (test / offline mode) ──────────────────────────────────


def _build_mock_tools() -> dict[str, list]:
    """
    Wrap mcp_server Python functions directly as LangChain tools.
    No HTTP required — imports from the local mcp_servers package.
    """
    # Import the raw async functions
    from mcp_servers.db_server import describe_table, list_tables, query_database
    from mcp_servers.files_server import lint_python, list_files, read_file, write_file
    from mcp_servers.search_server import fetch_url, web_search

    # LangChain's @tool decorator works on async functions
    # We re-decorate here so the tool name/description matches the MCP schema
    @lc_tool
    async def _web_search(query: str, max_results: int = 5) -> list[dict]:
        """Search the web for recent information."""
        return await web_search(query, max_results)

    @lc_tool
    async def _fetch_url(url: str) -> str:
        """Fetch the plain-text content of a URL."""
        return await fetch_url(url)

    @lc_tool
    async def _query_database(sql: str) -> list[dict]:
        """Execute a read-only SQL SELECT query against the company_ops database."""
        return await query_database(sql)

    @lc_tool
    async def _list_tables() -> list[str]:
        """List all available tables in the company_ops schema."""
        return await list_tables()

    @lc_tool
    async def _describe_table(table_name: str) -> dict:
        """Describe the columns of a table in the company_ops schema."""
        return await describe_table(table_name)

    @lc_tool
    async def _read_file(path: str) -> str:
        """Read the content of a file within the sandbox."""
        return await read_file(path)

    @lc_tool
    async def _write_file(path: str, content: str) -> dict:
        """Write content to a file within the sandbox."""
        return await write_file(path, content)

    @lc_tool
    async def _list_files(path: str = "") -> list[str]:
        """List files and directories within the sandbox."""
        return await list_files(path)

    @lc_tool
    async def _lint_python(path: str) -> dict:
        """Run ruff static analysis on a Python file within the sandbox."""
        return await lint_python(path)

    return {
        "researcher": [_web_search, _fetch_url],
        "analyst": [_query_database, _list_tables, _describe_table],
        "coder": [_read_file, _write_file, _list_files, _lint_python],
    }


# ── MCP HTTP tool loading (production) ────────────────────────────────────────


async def _build_mcp_tools() -> dict[str, list]:
    """
    Load tools from the 3 HTTP MCP servers via MultiServerMCPClient.
    Requires the mcp-db, mcp-search, mcp-files containers to be running.
    """
    from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore

    server_config = {
        "db": {
            "url": settings.MCP_DB_URL,
            "transport": "streamable_http",
            "headers": {"Authorization": f"Bearer {settings.MCP_SERVER_KEY}"},
        },
        "search": {
            "url": settings.MCP_SEARCH_URL,
            "transport": "streamable_http",
            "headers": {"Authorization": f"Bearer {settings.MCP_SERVER_KEY}"},
        },
        "files": {
            "url": settings.MCP_FILES_URL,
            "transport": "streamable_http",
            "headers": {"Authorization": f"Bearer {settings.MCP_SERVER_KEY}"},
        },
    }

    client = MultiServerMCPClient(server_config)
    all_tools = await client.get_tools()

    # Partition by tool name prefix
    researcher_tools = [t for t in all_tools if t.name in {"web_search", "fetch_url"}]
    analyst_tools = [
        t for t in all_tools if t.name in {"query_database", "list_tables", "describe_table"}
    ]
    coder_tools = [
        t for t in all_tools if t.name in {"read_file", "write_file", "list_files", "lint_python"}
    ]

    logger.info(
        "mcp_tools_loaded",
        researcher=len(researcher_tools),
        analyst=len(analyst_tools),
        coder=len(coder_tools),
    )

    return {
        "researcher": researcher_tools,
        "analyst": analyst_tools,
        "coder": coder_tools,
    }


# ── Public factory ────────────────────────────────────────────────────────────


async def load_agent_tools(use_mock: bool = False) -> dict[str, list]:
    """
    Load tools for all specialist agents.

    Args:
        use_mock: Force mock mode even if SEARCH_PROVIDER != "mock".

    Returns:
        dict with keys "researcher", "analyst", "coder", each a list of BaseTool.
    """
    if use_mock or settings.SEARCH_PROVIDER == "mock":
        logger.info("tools_mode", mode="mock")
        return _build_mock_tools()

    import asyncio

    max_retries = 5
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            return await _build_mcp_tools()
        except Exception as exc:
            if attempt == max_retries - 1:
                logger.error(
                    "mcp_tools_failed_degraded",
                    exc=str(exc),
                    attempts=max_retries,
                    fallback="empty_tools",
                )
                # Graceful degradation: boot without tools rather than crashing the API.
                # Auth, health, and other non-agent endpoints will still work.
                # The MCP servers can be started and the API restarted to pick them up.
                return {"researcher": [], "analyst": [], "coder": []}

            delay = base_delay * (2**attempt)
            logger.warning(
                "mcp_tools_connection_retry", attempt=attempt + 1, delay=delay, exc=str(exc)
            )
            await asyncio.sleep(delay)

    return {"researcher": [], "analyst": [], "coder": []}
