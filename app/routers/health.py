"""
app/routers/health.py - public liveness endpoint.

Detailed MCP diagnostics live behind auth in app/routers/agent_router.py.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(tags=["health"])
_BOOT_TIME = time.monotonic()


@router.get("/api/health")
async def health() -> dict:
    """Fast liveness check for load balancers and keep-alive jobs."""
    uptime = time.monotonic() - _BOOT_TIME
    return {
        "status": "ok",
        "ts": datetime.now(UTC).isoformat(),
        "version": "0.1.0",
        "uptime_seconds": round(uptime, 1),
        "cold_start": uptime < 60,
    }
