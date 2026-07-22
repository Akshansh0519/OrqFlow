"""
app/config.py — OrqFlow application settings.

All configuration is read from environment variables via pydantic-settings.
Zero hardcoded values — see .env.example for every variable.

Section 17.5 (Deployment Hardening):
  - CLIENT_URL supports comma-separated origins for multiple CORS targets.
  - REDIS_URL auto-detection for managed providers lives in redis_connection_kwargs().
  - API_BASE_URL is optional; when set, FastAPI's Swagger UI "servers" list is configured.
  - PORT is intentionally NOT in Settings — it is read by the Dockerfile CMD directly.
"""

from __future__ import annotations

import ssl
from functools import cached_property
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str
    MCP_DATABASE_URL: str | None = None

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str
    REDIS_SOCKET_TIMEOUT: int = 5  # seconds — prevents infinite hangs (§17.5.4)

    # ── JWT ───────────────────────────────────────────────────────────────────
    ACCESS_TOKEN_SECRET: str
    REFRESH_TOKEN_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS (§17.5.5) ────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins.
    # "http://localhost:5173" for dev, add deployed URL for prod.
    # NEVER use "*" with allow_credentials=True — browsers reject it.
    CLIENT_URL: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ── MCP Auth ─────────────────────────────────────────────────────────────
    MCP_SERVER_KEY: str  # Shared bearer key for all 3 MCP servers

    # ── MCP Server URLs (§17.5.1 — from env, never hardcoded) ────────────────
    MCP_DB_URL: str = "http://mcp-db:8001/mcp"
    MCP_SEARCH_URL: str = "http://mcp-search:8002/mcp"
    MCP_FILES_URL: str = "http://mcp-files:8003/mcp"

    # ── Search ────────────────────────────────────────────────────────────────
    SEARCH_PROVIDER: str = "tavily"  # "tavily" | "mock"
    TAVILY_API_KEY: str = ""

    # ── LLM Models (Card 9 — model tiering) ──────────────────────────────────
    ROUTER_LLM_MODEL: str = "llama-3.3-70b-versatile"
    WORKER_LLM_MODEL: str = "llama-3.3-70b-versatile"
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # ── Rate Limits (Card 10) ─────────────────────────────────────────────────
    USER_RUNS_PER_MINUTE: int = 10
    TOOL_CALLS_PER_RUN: int = 20

    # ── Deployment (§17.5.7 — optional, blank for local dev) ─────────────────
    # When set, Swagger UI "servers" list shows this URL so "Try it out" works
    # on the deployed site without pointing back to localhost.
    API_BASE_URL: str = ""
    USE_IN_MEMORY_STORAGE: bool = False
    ENVIRONMENT: str = "development"

    # ── Computed properties ───────────────────────────────────────────────────

    @cached_property
    def allowed_origins(self) -> list[str]:
        """
        Split CLIENT_URL on commas so we support multiple origins.
        Example: "https://orqflow.vercel.app,http://localhost:5173"
        """
        return [origin.strip() for origin in self.CLIENT_URL.split(",") if origin.strip()]

    @cached_property
    def redis_ssl_kwargs(self) -> dict:
        """
        Auto-detect managed Redis providers and return SSL kwargs.
        Prevents the ShopSense bug: connection closed errors on Upstash
        because SSL was not enabled. (§17.5.3)

        Detection logic:
          - rediss:// scheme  → SSL required (standard managed Redis indicator)
          - upstash.io domain → always SSL
          - redis.cloud domain → always SSL
          - aivencloud.com domain → always SSL
        """
        url = self.REDIS_URL
        needs_ssl = (
            url.startswith("rediss://")
            or "upstash.io" in url
            or "redis.cloud" in url
            or "aivencloud.com" in url
        )
        if needs_ssl:
            return {
                "ssl_cert_reqs": ssl.CERT_REQUIRED,
            }
        return {}

    @cached_property
    def redis_client_kwargs(self) -> dict:
        """
        Full kwargs for constructing a Redis client.
        Merges SSL detection with timeout settings.
        Socket timeout prevents infinite hanging on free-tier Redis drops (§17.5.4).
        """
        return {
            "socket_timeout": self.REDIS_SOCKET_TIMEOUT,
            "socket_connect_timeout": self.REDIS_SOCKET_TIMEOUT,
            "retry_on_timeout": True,
            "decode_responses": False,  # LangGraph checkpointer needs bytes
            **self.redis_ssl_kwargs,
        }

    @cached_property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"prod", "production"}

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Self:
        """Keep local setup easy, but fail fast on unsafe production config."""
        if not self.is_production:
            return self

        secrets = {
            "ACCESS_TOKEN_SECRET": self.ACCESS_TOKEN_SECRET,
            "REFRESH_TOKEN_SECRET": self.REFRESH_TOKEN_SECRET,
            "MCP_SERVER_KEY": self.MCP_SERVER_KEY,
        }
        weak = [name for name, value in secrets.items() if len(value) < 32]
        if weak:
            raise ValueError(
                "Production secrets must be at least 32 characters: " + ", ".join(weak)
            )
        if self.ACCESS_TOKEN_SECRET == self.REFRESH_TOKEN_SECRET:
            raise ValueError("ACCESS_TOKEN_SECRET and REFRESH_TOKEN_SECRET must differ")
        if not self.MCP_DATABASE_URL:
            raise ValueError("MCP_DATABASE_URL is required in production")
        return self


# Singleton — import this everywhere, never re-instantiate.
settings = Settings()
