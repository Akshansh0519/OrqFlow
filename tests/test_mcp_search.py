"""
tests/test_mcp_search.py — Phase 2 acceptance tests for the Search MCP server.

Tests the search tools in mock mode (SEARCH_PROVIDER=mock in .env):
  ✅ web_search returns a list of dicts with required fields
  ✅ web_search max_results is respected
  ✅ web_search with empty query raises ValueError
  ✅ fetch_url returns mock content
  ✅ fetch_url with non-http URL raises ValueError
  ✅ Mock results are deterministic (same input = same output)
"""

from __future__ import annotations

import pytest

from mcp_servers.search_server import web_search, fetch_url


@pytest.mark.anyio
async def test_web_search_returns_list():
    results = await web_search("LangGraph tutorial")
    assert isinstance(results, list)
    assert len(results) > 0


@pytest.mark.anyio
async def test_web_search_result_shape():
    results = await web_search("FastMCP")
    for r in results:
        assert "title" in r, f"Missing 'title' key: {r}"
        assert "url" in r, f"Missing 'url' key: {r}"
        assert "snippet" in r, f"Missing 'snippet' key: {r}"


@pytest.mark.anyio
async def test_web_search_max_results_respected():
    results = await web_search("test query", max_results=1)
    assert len(results) <= 1


@pytest.mark.anyio
async def test_web_search_max_results_capped_at_10():
    """max_results > 10 should be silently capped."""
    results = await web_search("test query", max_results=999)
    assert len(results) <= 10


@pytest.mark.anyio
async def test_web_search_empty_query_raises():
    with pytest.raises(ValueError, match="empty"):
        await web_search("")


@pytest.mark.anyio
async def test_web_search_whitespace_query_raises():
    with pytest.raises(ValueError, match="empty"):
        await web_search("   ")


@pytest.mark.anyio
async def test_web_search_mock_is_deterministic():
    """Same query should always return the same results in mock mode."""
    r1 = await web_search("anything", max_results=3)
    r2 = await web_search("anything", max_results=3)
    assert r1 == r2


@pytest.mark.anyio
async def test_fetch_url_returns_string():
    content = await fetch_url("https://example.com")
    assert isinstance(content, str)
    assert len(content) > 0


@pytest.mark.anyio
async def test_fetch_url_mock_contains_url():
    content = await fetch_url("https://example.com/test-page")
    assert "example.com" in content


@pytest.mark.anyio
async def test_fetch_url_non_http_raises():
    with pytest.raises(ValueError, match="http"):
        await fetch_url("ftp://example.com")


@pytest.mark.anyio
async def test_fetch_url_no_scheme_raises():
    with pytest.raises(ValueError, match="http"):
        await fetch_url("example.com")
