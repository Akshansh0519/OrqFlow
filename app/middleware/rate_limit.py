"""
app/middleware/rate_limit.py — Redis sliding-window rate limiter middleware.

Implements Card 10's sliding window algorithm using Redis sorted sets:
  - Budget 1: ratelimit:user_run:{user_id} — checked on POST /api/threads/{id}/run
  - Budget 2: ratelimit:tool_calls:{run_id} — handled at graph/node level

Sliding Window Pipeline (atomic / pipelined):
  1. ZREMRANGEBYSCORE key 0 (now - window) -> remove expired timestamps
  2. ZADD key {now: now}                  -> add current request timestamp
  3. ZCARD key                            -> count active requests in window
  4. EXPIRE key window                    -> ensure key ttl

Graceful Degradation (§17.5.4):
  If Redis connection drops, times out, or package is missing, log a warning
  and FAIL OPEN (allow the request). A temporarily unlimited API is better than a dead API.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = structlog.get_logger()

# Global redis client for rate limiting (initialized lazily)
_redis_client: Any = None


def get_redis_client() -> Any:
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as redis

            _redis_client = redis.Redis.from_url(
                settings.REDIS_URL,
                **settings.redis_client_kwargs,
            )
        except ImportError:
            raise RuntimeError("redis package not installed")
    return _redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only rate limit the agent run endpoint
        if request.method == "POST" and "/run" in request.url.path:
            auth_header = request.headers.get("Authorization")
            user_key = "anon"
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    import jwt

                    token = auth_header.split(" ")[1]
                    payload = jwt.decode(token, options={"verify_signature": False})
                    user_key = payload.get("sub", "anon")
                except Exception:
                    user_key = request.client.host if request.client else "anon"
            else:
                user_key = request.client.host if request.client else "anon"

            key = f"ratelimit:user_run:{user_key}"
            now = time.time()
            window = 60  # 1 minute sliding window
            limit = settings.USER_RUNS_PER_MINUTE

            try:
                r = get_redis_client()
                async with r.pipeline(transaction=True) as pipe:
                    pipe.zremrangebyscore(key, 0, now - window)
                    pipe.zadd(key, {str(now): now})
                    pipe.zcard(key)
                    pipe.expire(key, window + 1)
                    results = await pipe.execute()

                request_count = results[2]
                if request_count > limit:
                    logger.warning(
                        "rate_limit_exceeded",
                        user_key=user_key,
                        count=request_count,
                        limit=limit,
                    )
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "Rate limit exceeded",
                            "code": "RATE_LIMITED",
                            "details": {
                                "message": f"Maximum {limit} agent runs per minute exceeded. Please try again soon."
                            },
                        },
                    )
            except Exception as exc:
                # Graceful degradation (§17.5.4): Fail open if Redis drops or missing
                logger.warning("rate_limiter_redis_error_fail_open", error=str(exc))

        return await call_next(request)
