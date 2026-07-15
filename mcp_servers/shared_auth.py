"""
mcp_servers/shared_auth.py — Shared bearer key authentication for all MCP servers.

Every MCP server validates the same MCP_SERVER_KEY from the Authorization header.
This is separate from the app's user-level JWT — a tool server should not implicitly
trust "the request came from our own app," since the point of Card 2 is that ANY
MCP-compatible client can connect. The shared key is a simple gate: is this a
known caller, not: who is this user?
"""

from __future__ import annotations

from fastmcp.server.dependencies import get_http_request
from app.config import settings


def mcp_auth_required() -> bool:
    """Mock mode is used by tests/direct function calls and has no HTTP request."""
    return settings.SEARCH_PROVIDER != "mock"


def verify_mcp_key() -> None:
    """
    Validate the Bearer token from the current HTTP request.

    Raises:
        PermissionError: If the Authorization header is missing or the token is wrong.

    Called at the top of each tool function that should be gated.
    """
    if not mcp_auth_required():
        return

    request = get_http_request()
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise PermissionError("Missing Authorization header")

    token = auth_header.removeprefix("Bearer ").strip()
    if token != settings.MCP_SERVER_KEY:
        raise PermissionError("Invalid MCP server key")
