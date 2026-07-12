"""
app/errors.py — Application error types and global exception handlers.

ALL errors in OrqFlow return this JSON shape:
    {"error": string, "code"?: string, "details"?: object, "hint"?: string}

The "hint" field (§17.5.6) is used for deployment-specific errors like cold starts.
FastAPI's default 422 shape is replaced — never let it leak to clients.
"""

from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


class AppError(Exception):
    """
    Raise this anywhere in the app to return a structured JSON error response.

    Usage:
        raise AppError("Thread not found", status_code=404, code="NOT_FOUND")
        raise AppError("Rate limit exceeded", status_code=429, code="RATE_LIMITED")
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str | None = None,
        hint: str | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.hint = hint
        super().__init__(message)


def register_error_handlers(app) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        body: dict = {"error": exc.message}
        if exc.code:
            body["code"] = exc.code
        if exc.hint:
            body["hint"] = exc.hint
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Replace FastAPI's default 422 with our standard shape."""
        return JSONResponse(
            status_code=400,
            content={"error": "Validation failed", "details": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all for any exception that wasn't handled.
        Log it with structlog (preserves request context), return 500.
        Includes a hint for cold-start style timeouts (§17.5.6).
        """
        logger.error(
            "unhandled_error",
            path=str(request.url.path),
            method=request.method,
            exc_type=type(exc).__name__,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "hint": (
                    "If this is the first request after a period of inactivity, "
                    "the server may be cold-starting. Please retry in 30 seconds."
                ),
            },
        )
