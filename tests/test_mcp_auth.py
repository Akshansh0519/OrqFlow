"""
tests/test_mcp_auth.py - shared MCP bearer authentication.

Tool behavior is mostly tested in mock mode, so this file tests the auth
primitive directly without starting HTTP servers.
"""

from __future__ import annotations

import pytest

from app.config import settings
from mcp_servers import shared_auth


class _Request:
    def __init__(self, authorization: str = "") -> None:
        self.headers = {"Authorization": authorization} if authorization else {}


def test_verify_mcp_key_allows_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "SEARCH_PROVIDER", "mock")
    shared_auth.verify_mcp_key()


def test_verify_mcp_key_rejects_missing_header(monkeypatch):
    monkeypatch.setattr(settings, "SEARCH_PROVIDER", "tavily")
    monkeypatch.setattr(settings, "MCP_SERVER_KEY", "correct-key")
    monkeypatch.setattr(shared_auth, "get_http_request", lambda: _Request())

    with pytest.raises(PermissionError, match="Missing Authorization"):
        shared_auth.verify_mcp_key()


def test_verify_mcp_key_rejects_wrong_key(monkeypatch):
    monkeypatch.setattr(settings, "SEARCH_PROVIDER", "tavily")
    monkeypatch.setattr(settings, "MCP_SERVER_KEY", "correct-key")
    monkeypatch.setattr(
        shared_auth,
        "get_http_request",
        lambda: _Request("Bearer wrong-key"),
    )

    with pytest.raises(PermissionError, match="Invalid MCP"):
        shared_auth.verify_mcp_key()


def test_verify_mcp_key_accepts_correct_key(monkeypatch):
    monkeypatch.setattr(settings, "SEARCH_PROVIDER", "tavily")
    monkeypatch.setattr(settings, "MCP_SERVER_KEY", "correct-key")
    monkeypatch.setattr(
        shared_auth,
        "get_http_request",
        lambda: _Request("Bearer correct-key"),
    )

    shared_auth.verify_mcp_key()
