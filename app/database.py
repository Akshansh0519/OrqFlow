"""
app/database.py — Async SQLAlchemy engine and session factory.

Engine is created lazily on first use so that:
  1. Tests that override get_db never import asyncpg (not installed locally).
  2. Alembic env.py builds its own engine directly from DATABASE_URL.

Imports:
  - app/dependencies.py (get_db) calls get_async_session()
  - alembic/env.py builds its own engine — does NOT import this module
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

_engine = None
_async_session: async_sessionmaker[AsyncSession] | None = None


def _get_engine():
    """Return the singleton async engine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def get_async_session() -> async_sessionmaker[AsyncSession]:
    """Return the singleton session factory, creating it on first call."""
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session
