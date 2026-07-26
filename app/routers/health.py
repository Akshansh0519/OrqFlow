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


async def ping_all_services() -> None:
    """Fire-and-forget pings to wake up all 4 services on Render free tier.

    Pings:
      - MCP DB server (strips /mcp to hit root)
      - MCP Search server (strips /mcp to hit root)
      - MCP Files server (strips /mcp to hit root)
      - Main API itself (via API_BASE_URL if set, so Render keeps it warm)
    """
    mcp_urls = [
        settings.MCP_DB_URL,
        settings.MCP_SEARCH_URL,
        settings.MCP_FILES_URL,
    ]
    # Build base URLs from /mcp endpoints
    base_urls = [u.split("/mcp")[0] for u in mcp_urls if u]

    # Also ping the main API itself if deployed (keeps this Render service warm too)
    if settings.API_BASE_URL:
        base_urls.append(settings.API_BASE_URL.rstrip("/"))

    # Short timeout — we just need to initiate the TCP connection to wake Render up.
    async with httpx.AsyncClient(timeout=2.0) as client:
        for url in base_urls:
            try:
                await client.get(url)
            except Exception:
                pass  # Timeouts/errors are expected while servers sleep — ignore them


@router.get("/api/health")
async def health(background_tasks: BackgroundTasks) -> dict:
    """Fast liveness check for load balancers and keep-alive jobs.

    Every hit triggers a background ping to all 4 Render services:
    the 3 MCP servers and the main API itself. This is called by the
    frontend BackendStatusBanner on every page load, guaranteeing all
    services receive a wake-up signal even if they were sleeping.
    """
    background_tasks.add_task(ping_all_services)

    uptime = time.monotonic() - _BOOT_TIME
    return {
        "status": "ok",
        "ts": datetime.now(UTC).isoformat(),
        "version": "0.1.0",
        "uptime_seconds": round(uptime, 1),
        "cold_start": uptime < 60,
    }
