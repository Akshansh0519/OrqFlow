"""
app/main.py — FastAPI application factory and lifespan.

Middleware stack order (ORDER MATTERS — each layer wraps those below it):
  1. CORSMiddleware     — handles preflight before anything else touches the request
  2. RequestIDMiddleware — assigns X-Request-ID for log correlation
  (Rate limiter is added as a FastAPI dependency on the /run route, not global middleware,
   because it needs the authenticated user_id which requires JWT resolution first.)

Lifespan:
  - Initializes checkpointer (Redis), store (Postgres), and MCP tools at startup.
  - Stores singletons on app.state so routers can access them via request.app.state.
  - These are initialized once and reused for every request.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.errors import register_error_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.routers import health

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: initialize shared resources.
    Shutdown: clean up if needed.

    Resources stored on app.state:
      - checkpointer: AsyncRedisSaver (short-term memory, Card 3)
      - store: AsyncPostgresStore (long-term facts, Card 4)
      - agent_tools: dict[str, list] of LangChain tools per specialist
      - graph: compiled LangGraph graph

    These are imported lazily here (not at module level) so Phase 0 boots
    cleanly without requiring LangGraph/MCP servers to exist yet.
    """
    logger.info("orqflow_starting", version="0.1.0")

    # ── Phase 3: Memory + Tools + Graph ──────────────────────────────────────
    from app.graph.builder import build_graph
    from app.graph.memory import get_checkpointer, get_store
    from app.graph.tools import load_agent_tools

    use_memory = settings.USE_IN_MEMORY_STORAGE
    app.state.checkpointer = await get_checkpointer(use_memory=use_memory)
    app.state.store = await get_store(use_memory=use_memory)
    app.state.agent_tools = await load_agent_tools()

    uncompiled = build_graph(app.state.agent_tools)
    app.state.graph = uncompiled.compile(
        checkpointer=app.state.checkpointer,
        store=app.state.store,
    )

    logger.info(
        "orqflow_ready",
        tools={k: len(v) for k, v in app.state.agent_tools.items()},
        graph_nodes=list(app.state.graph.get_graph().nodes.keys()),
    )

    yield

    # Shutdown cleanup (add connection pool teardown here when Phase 3 is wired)
    logger.info("orqflow_shutdown")


def create_app() -> FastAPI:
    """
    Application factory — builds and returns the configured FastAPI instance.

    Swagger UI (§17.5.7):
      - servers list populated from API_BASE_URL env var so "Try it out"
        works on the deployed site, not just localhost.
      - /docs and /openapi.json are NOT behind any auth — Swagger UI must
        reach the OpenAPI spec unauthenticated.
    """
    servers = []
    if settings.API_BASE_URL:
        servers = [{"url": settings.API_BASE_URL, "description": "Deployed"}]

    app = FastAPI(
        title="OrqFlow",
        description=(
            "Multi-agent AI orchestration platform. "
            "A LangGraph supervisor routes tasks to specialist agents via MCP tool servers."
        ),
        version="0.1.0",
        servers=servers,
        lifespan=lifespan,
        # /docs and /openapi.json must be reachable unauthenticated (§17.5.7)
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # ── Middleware (ORDER MATTERS) ─────────────────────────────────────────────
    # 1. CORS — must be first so preflight OPTIONS requests are handled before
    #    any auth middleware can reject them.
    #    NEVER use allow_origins=["*"] with allow_credentials=True (§17.5.5).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Request ID — propagates X-Request-ID for log correlation
    app.add_middleware(RequestIDMiddleware)

    # 3. Rate limiter — sliding window rate limiting on /run endpoint
    app.add_middleware(RateLimitMiddleware)

    # ── Error handlers ─────────────────────────────────────────────────────────
    register_error_handlers(app)

    # ── Routers ────────────────────────────────────────────────────────────────
    # Phase 1: Auth
    from app.routers import agent_router, auth_router

    app.include_router(health.router)
    app.include_router(auth_router.router)
    app.include_router(agent_router.router)
    # Phase 4+ routers added here as they are implemented:
    # from app.routers import threads, run, trace, facts
    # app.include_router(threads.router)
    # app.include_router(run.router)
    # app.include_router(trace.router)
    # app.include_router(facts.router)

    return app


app = create_app()
