"""
tests/conftest.py — Shared pytest fixtures for the OrqFlow test suite.

Database strategy:
  - Phase 0 (health): no DB needed — in-process ASGI client only
  - Phase 1+ (auth, threads, etc.): SQLite in-memory via aiosqlite
    Same SQLAlchemy models, no Docker required for unit tests.
    Integration tests (MCP, SSE, memory) run against real Postgres in CI.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.models import Base

# ── Test database (SQLite in-memory) ─────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session", autouse=True)
def _force_mock_search_for_tests():
    settings.SEARCH_PROVIDER = "mock"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def test_engine():
    """
    Create a single async SQLite engine for the whole test session.
    All tables are created once and shared across tests via transactions.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """
    Yield a per-test async session that rolls back after each test.
    This keeps tests isolated without recreating tables each time.
    """
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def async_client(db_session):
    """
    HTTP client that communicates with the FastAPI app in-process.
    Overrides the get_db dependency to use the test SQLite session.
    """
    from app.dependencies import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
