"""
app/graph/memory.py — Checkpointer and long-term store factories.

Short-term memory  → AsyncRedisSaver (per-thread conversation checkpoints)
Long-term memory   → AsyncPostgresStore (cross-thread facts, user preferences)

Both use lazy initialization: the factory functions are called once at startup
in app/main.py lifespan and stored on app.state.

Test/offline mode (SEARCH_PROVIDER=mock):
  → MemorySaver (in-memory, zero deps)
  → InMemoryStore (in-memory, zero deps)

Redis SSL hardening (§17.5.3/17.5.4):
  → ssl_kwargs and socket_timeout injected from app/config.py
  → Never assume plaintext Redis in production

interview_answer: "Why two memory layers?"
  "Redis handles short-term: checkpoint every graph step so the run can resume
  after a crash or timeout. Postgres handles long-term: facts the user tells
  the agent persist across conversations — name, preferences, project context.
  Mixing both in Redis would lose long-term facts on eviction. Mixing both in
  Postgres would make every step a slow synchronous DB write."
"""

from __future__ import annotations

import structlog

from app.config import settings

logger = structlog.get_logger()


async def get_checkpointer(use_memory: bool = False):
    """
    Return the short-term memory checkpointer.

    Args:
        use_memory: If True, use in-memory saver (tests / offline dev).
                    If False, use AsyncRedisSaver (production).

    Returns:
        A LangGraph checkpointer compatible with .compile(checkpointer=...).
    """
    if use_memory or settings.USE_IN_MEMORY_STORAGE:
        from langgraph.checkpoint.memory import MemorySaver

        logger.info("checkpointer_mode", mode="memory")
        return MemorySaver()

    # Production: Redis with SSL + timeout (§17.5.3 / §17.5.4)
    try:
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver

        saver = AsyncRedisSaver(
            settings.REDIS_URL,
            connection_args=settings.redis_client_kwargs,
        )
        await saver.__aenter__()
        logger.info("checkpointer_mode", mode="redis", url=settings.REDIS_URL[:30])
        return saver

    except Exception as exc:
        if settings.is_production:
            raise
        # Graceful degradation: fall back to in-memory and log the failure
        logger.error(
            "redis_checkpointer_failed",
            exc=str(exc),
            fallback="MemorySaver",
        )
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()


async def get_store(use_memory: bool = False):
    """
    Return the long-term memory store.

    Args:
        use_memory: If True, use InMemoryStore (tests / offline dev).
                    If False, use AsyncPostgresStore (production).

    Returns:
        A LangGraph store compatible with .compile(store=...).
    """
    if use_memory or settings.USE_IN_MEMORY_STORAGE:
        from langgraph.store.memory import InMemoryStore

        logger.info("store_mode", mode="memory")
        return InMemoryStore()

    # Production: Postgres via asyncpg
    try:
        from langgraph.store.postgres.aio import AsyncPostgresStore
        from psycopg.rows import dict_row
        from psycopg_pool import AsyncConnectionPool

        db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        pool = AsyncConnectionPool(
            db_url,
            min_size=1,
            max_size=10,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            open=False,
        )
        await pool.open()
        store = AsyncPostgresStore(conn=pool)
        await store.setup()  # creates langgraph_store table if needed
        logger.info("store_mode", mode="postgres", url=settings.DATABASE_URL[:30])
        return store

    except Exception as exc:
        if settings.is_production:
            raise
        logger.error(
            "postgres_store_failed",
            exc=str(exc),
            fallback="InMemoryStore",
        )
        from langgraph.store.memory import InMemoryStore

        return InMemoryStore()
