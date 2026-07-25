"""
app/routers/health.py - public liveness endpoint.

Detailed MCP diagnostics live behind auth in app/routers/agent_router.py.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, BackgroundTasks

from app.config import settings

router = APIRouter(tags=["health"])
_BOOT_TIME = time.monotonic()


async def ping_mcp_servers() -> None:
    """Fire-and-forget pings to wake up MCP servers on Render free tier."""
    urls = [
        settings.MCP_DB_URL,
        settings.MCP_SEARCH_URL,
        settings.MCP_FILES_URL,
    ]
    # We just need to hit the server to wake it up. Short timeout so we don't hang.
    async with httpx.AsyncClient(timeout=2.0) as client:
        for url in urls:
            if not url:
                continue
            try:
                # Stripping /mcp to just hit the root of the server
                base_url = url.split("/mcp")[0]
                await client.get(base_url)
            except Exception:
                pass  # Ignore timeouts/errors, the ping itself wakes Render up


@router.get("/api/health")
async def health(background_tasks: BackgroundTasks) -> dict:
    """Fast liveness check for load balancers and keep-alive jobs."""
    # Ping the MCP servers in the background so it doesn't block this response
    background_tasks.add_task(ping_mcp_servers)

    uptime = time.monotonic() - _BOOT_TIME
    return {
        "status": "ok",
        "ts": datetime.now(UTC).isoformat(),
        "version": "0.1.0",
        "uptime_seconds": round(uptime, 1),
        "cold_start": uptime < 60,
    }
