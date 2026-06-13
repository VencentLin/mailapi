"""Shared test fixtures for backend integration tests.

Fixtures here are auto-discovered by pytest; individual test modules should
import only the helpers / utilities they need (e.g. ``login_as``).
"""

from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.db.session import get_db_session
from backend.app.main import create_app
from backend.app.models import (  # noqa: F401
    ApiKey,
    AuditLog,
    MailAccount,
    MailAccountClaim,
    MailFetchLog,
)
from backend.app.models.base import Base

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite://"

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_engine():
    """Create a fresh async SQLite engine with all tables, per test session."""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncSession:
    """Provide an async SQLite session scoped to a single test."""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_session):
    """Return an httpx AsyncClient wired to the FastAPI app with test DB."""
    app = create_app()

    async def override_get_db_session():
        yield test_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
