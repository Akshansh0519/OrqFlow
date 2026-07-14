"""
app/middleware/request_id.py — X-Request-ID injection middleware.

Assigns a unique UUID to every incoming request and propagates it on the
response. This makes log correlation trivial: every structlog line in a
request handler includes the request_id via context binding.

Usage in logs:
    log = structlog.get_logger().bind(request_id=request.state.request_id)
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Use incoming header if present (e.g. from a load balancer), else generate
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
