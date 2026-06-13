# MailAPI Phase 1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the runnable local-development foundation plus the final server Docker deployment artifact: FastAPI backend, PostgreSQL/Alembic schema baseline, Vue admin shell, Docker image definition with internal Redis, and repeatable verification commands.

**Architecture:** Use a monorepo with `backend/` for FastAPI and `frontend/` for Vue. Local development runs FastAPI and Vite directly on the host without Docker. FastAPI owns API routes and serves the built Vue `dist` in production; Redis runs inside the final Docker container for cache/short-lived state, while PostgreSQL remains an external cloud database.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x async, Alembic, asyncpg, Redis, pytest, Vue 3, Vite, Element Plus, Pinia, Docker.

---

## Scope Check

The full design covers several independent subsystems: authentication, mailbox ownership, Outlook OAuth2/Graph, IMAP fallback, verification-code extraction, logs, frontend, and deployment. This plan intentionally covers only Phase 1 foundation. Later phases should each receive their own implementation plan and Claude task files.

Phase 1 is complete when:

- Backend imports and health endpoint work.
- Database models and Alembic baseline exist.
- Local backend and frontend commands are documented and runnable without Docker.
- Dockerfile and entrypoint exist for final server deployment; Docker build is verified only on a machine where Docker is available.
- Vue admin shell builds and can be served by FastAPI.
- Verification commands are documented and runnable.

## File Structure

Create this structure:

```text
backend/
  app/
    __init__.py
    main.py
    api/
      __init__.py
      router.py
      routes/
        __init__.py
        health.py
    core/
      __init__.py
      config.py
    db/
      __init__.py
      base.py
      session.py
    models/
      __init__.py
      api_key.py
      base.py
      enums.py
      logs.py
      mail_account.py
      user.py
  migrations/
    env.py
    script.py.mako
    versions/
      20260613_0001_foundation_schema.py
docker/
  entrypoint.sh
frontend/
  index.html
  package.json
  tsconfig.json
  tsconfig.app.json
  tsconfig.node.json
  vite.config.ts
  src/
    App.vue
    main.ts
    router/
      index.ts
    stores/
      auth.ts
    views/
      DashboardView.vue
      LoginView.vue
tests/
  backend/
    test_database_metadata.py
    test_health.py
alembic.ini
Dockerfile
.env.example
pyproject.toml
```

Responsibilities:

- `backend/app/main.py`: app factory, API router registration, frontend static fallback.
- `backend/app/core/config.py`: environment-backed settings.
- `backend/app/api/routes/health.py`: health endpoints used by tests and deployment checks.
- `backend/app/db/session.py`: async SQLAlchemy engine/session factory.
- `backend/app/models/*`: initial schema models only; no business logic.
- `backend/migrations/*`: Alembic environment and first migration.
- `docker/entrypoint.sh`: starts Redis, optionally runs Alembic, then starts FastAPI.
- `frontend/src/*`: minimal authenticated-console shell; no real auth behavior yet.
- `tests/backend/*`: quick backend verification tests.

## Task 1: Backend Scaffold And Health Endpoint

**Files:**

- Create: `pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/api/routes/__init__.py`
- Create: `backend/app/api/routes/health.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `tests/backend/test_health.py`

- [ ] **Step 1: Write the failing health test**

Create `tests/backend/test_health.py`:

```python
from httpx import ASGITransport, AsyncClient
import pytest

from backend.app.main import create_app


@pytest.mark.asyncio
async def test_health_endpoint_returns_service_status():
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "MailAPI",
        "version": "0.1.0",
    }
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
pytest tests/backend/test_health.py -v
```

Expected: FAIL because `backend.app.main` does not exist yet.

- [ ] **Step 3: Add Python project dependencies**

Create `pyproject.toml`:

```toml
[project]
name = "mailapi"
version = "0.1.0"
description = "Outlook OAuth2 verification-code mail retrieval platform"
requires-python = ">=3.12"
dependencies = [
  "alembic>=1.16.0",
  "asyncpg>=0.30.0",
  "fastapi>=0.115.0",
  "greenlet>=3.1.0",
  "httpx>=0.28.0",
  "pydantic-settings>=2.7.0",
  "python-jose[cryptography]>=3.3.0",
  "redis>=5.2.0",
  "sqlalchemy[asyncio]>=2.0.36",
  "uvicorn[standard]>=0.34.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-asyncio>=0.25.0",
  "ruff>=0.8.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 4: Add backend app code**

Create `backend/app/core/config.py`:

```python
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MailAPI"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://mailapi:mailapi@localhost:5432/mailapi"
    redis_url: str = "redis://localhost:6379/0"
    run_migrations: bool = False
    frontend_dist_dir: Path = Path(__file__).resolve().parents[3] / "frontend" / "dist"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Create `backend/app/api/routes/health.py`:

```python
from fastapi import APIRouter

from backend.app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
```

Create `backend/app/api/router.py`:

```python
from fastapi import APIRouter

from backend.app.api.routes import health

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
```

Create `backend/app/main.py`:

```python
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.router import api_router
from backend.app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(api_router)
    mount_frontend(app, settings.frontend_dist_dir)
    return app


def mount_frontend(app: FastAPI, dist_dir: Path) -> None:
    assets_dir = dist_dir / "assets"
    index_file = dist_dir / "index.html"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    if not index_file.exists():
        return

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        return FileResponse(index_file)


app = create_app()
```

Create empty package files:

```text
backend/app/__init__.py
backend/app/api/__init__.py
backend/app/api/routes/__init__.py
backend/app/core/__init__.py
```

- [ ] **Step 5: Run the test and confirm it passes**

Run:

```bash
pytest tests/backend/test_health.py -v
```

Expected: PASS.

- [ ] **Step 6: Run lint for created backend files**

Run:

```bash
ruff check backend tests/backend
```

Expected: no errors.

- [ ] **Step 7: Commit**

Run:

```bash
git add pyproject.toml backend tests/backend/test_health.py
git commit -m "feat: scaffold fastapi backend"
```

## Task 2: Database Models And Alembic Baseline

**Files:**

- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/enums.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/api_key.py`
- Create: `backend/app/models/mail_account.py`
- Create: `backend/app/models/logs.py`
- Create: `alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/versions/20260613_0001_foundation_schema.py`
- Create: `tests/backend/test_database_metadata.py`

- [ ] **Step 1: Write metadata tests**

Create `tests/backend/test_database_metadata.py`:

```python
from backend.app.db.base import Base
from backend.app.models.enums import MailAccountOwnerType, UserRole


def test_foundation_tables_are_registered():
    expected_tables = {
        "users",
        "api_keys",
        "mail_accounts",
        "mail_account_claims",
        "mail_fetch_logs",
        "audit_logs",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))


def test_core_enum_values_match_design_doc():
    assert UserRole.ADMIN.value == "admin"
    assert UserRole.USER.value == "user"
    assert MailAccountOwnerType.USER.value == "user"
    assert MailAccountOwnerType.PUBLIC.value == "public"
```

- [ ] **Step 2: Run the metadata test and confirm it fails**

Run:

```bash
pytest tests/backend/test_database_metadata.py -v
```

Expected: FAIL because database modules do not exist yet.

- [ ] **Step 3: Add database base and session**

Create `backend/app/db/base.py`:

```python
from backend.app.models.base import Base

__all__ = ["Base"]
```

Create `backend/app/db/session.py`:

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 4: Add model base and enums**

Create `backend/app/models/base.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

Create `backend/app/models/enums.py`:

```python
from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class ApiKeyStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    EXPIRED = "expired"


class MailAccountOwnerType(StrEnum):
    USER = "user"
    PUBLIC = "public"


class MailAccountStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    INVALID = "invalid"
```

- [ ] **Step 5: Add foundation models**

Create `backend/app/models/user.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin
from backend.app.models.enums import UserRole, UserStatus


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    api_keys = relationship("ApiKey", back_populates="user")
    mail_accounts = relationship("MailAccount", back_populates="owner_user")
```

Create `backend/app/models/api_key.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin
from backend.app.models.enums import ApiKeyStatus


class ApiKey(TimestampMixin, Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[ApiKeyStatus] = mapped_column(Enum(ApiKeyStatus), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", back_populates="api_keys")
```

Create `backend/app/models/mail_account.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin
from backend.app.models.enums import MailAccountOwnerType, MailAccountStatus


class MailAccount(TimestampMixin, Base):
    __tablename__ = "mail_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    owner_type: Mapped[MailAccountOwnerType] = mapped_column(
        Enum(MailAccountOwnerType),
        nullable=False,
        index=True,
    )
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[MailAccountStatus] = mapped_column(Enum(MailAccountStatus), nullable=False)
    default_proxy: Mapped[str | None] = mapped_column(String(512))
    last_protocol: Mapped[str | None] = mapped_column(String(32))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    remark: Mapped[str | None] = mapped_column(String(500))
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_via: Mapped[str] = mapped_column(String(40), nullable=False)

    owner_user = relationship("User", foreign_keys=[owner_user_id], back_populates="mail_accounts")
```

Create `backend/app/models/logs.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin


class MailAccountClaim(Base):
    __tablename__ = "mail_account_claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    mail_account_id: Mapped[int] = mapped_column(ForeignKey("mail_accounts.id"), nullable=False)
    claimed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    previous_owner_type: Mapped[str] = mapped_column(String(40), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class MailFetchLog(TimestampMixin, Base):
    __tablename__ = "mail_fetch_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    api_key_id: Mapped[int | None] = mapped_column(ForeignKey("api_keys.id"), index=True)
    mail_account_id: Mapped[int | None] = mapped_column(ForeignKey("mail_accounts.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    mailbox: Mapped[str] = mapped_column(String(40), nullable=False)
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    source_protocol: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None]


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[str] = mapped_column(String(80), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    ip_address: Mapped[str | None] = mapped_column(String(80))
```

Create `backend/app/models/__init__.py`:

```python
from backend.app.models.api_key import ApiKey
from backend.app.models.logs import AuditLog, MailAccountClaim, MailFetchLog
from backend.app.models.mail_account import MailAccount
from backend.app.models.user import User

__all__ = [
    "ApiKey",
    "AuditLog",
    "MailAccount",
    "MailAccountClaim",
    "MailFetchLog",
    "User",
]
```

Create empty package file:

```text
backend/app/db/__init__.py
```

- [ ] **Step 6: Add Alembic files**

Create `alembic.ini`:

```ini
[alembic]
script_location = backend/migrations
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Create `backend/migrations/env.py`:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.app.core.config import get_settings
from backend.app.db.base import Base
import backend.app.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return get_settings().database_url.replace("+asyncpg", "")


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Create `backend/migrations/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

Create `backend/migrations/versions/20260613_0001_foundation_schema.py` manually so the first migration does not require a live PostgreSQL connection:

```python
"""foundation schema

Revision ID: 20260613_0001
Revises:
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa

revision = "20260613_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])

    op.create_table(
        "mail_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("owner_type", sa.String(length=20), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("default_proxy", sa.String(length=512), nullable=True),
        sa.Column("last_protocol", sa.String(length=32), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_via", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mail_accounts_email", "mail_accounts", ["email"], unique=True)
    op.create_index("ix_mail_accounts_owner_type", "mail_accounts", ["owner_type"])
    op.create_index("ix_mail_accounts_owner_user_id", "mail_accounts", ["owner_user_id"])

    op.create_table(
        "mail_account_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mail_account_id", sa.Integer(), sa.ForeignKey("mail_accounts.id"), nullable=False),
        sa.Column("claimed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("previous_owner_type", sa.String(length=40), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "mail_fetch_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("api_key_id", sa.Integer(), sa.ForeignKey("api_keys.id"), nullable=True),
        sa.Column("mail_account_id", sa.Integer(), sa.ForeignKey("mail_accounts.id"), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("mailbox", sa.String(length=40), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("source_protocol", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mail_fetch_logs_trace_id", "mail_fetch_logs", ["trace_id"])
    op.create_index("ix_mail_fetch_logs_user_id", "mail_fetch_logs", ["user_id"])
    op.create_index("ix_mail_fetch_logs_api_key_id", "mail_fetch_logs", ["api_key_id"])
    op.create_index("ix_mail_fetch_logs_mail_account_id", "mail_fetch_logs", ["mail_account_id"])
    op.create_index("ix_mail_fetch_logs_email", "mail_fetch_logs", ["email"])
    op.create_index("ix_mail_fetch_logs_error_code", "mail_fetch_logs", ["error_code"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_mail_fetch_logs_error_code", table_name="mail_fetch_logs")
    op.drop_index("ix_mail_fetch_logs_email", table_name="mail_fetch_logs")
    op.drop_index("ix_mail_fetch_logs_mail_account_id", table_name="mail_fetch_logs")
    op.drop_index("ix_mail_fetch_logs_api_key_id", table_name="mail_fetch_logs")
    op.drop_index("ix_mail_fetch_logs_user_id", table_name="mail_fetch_logs")
    op.drop_index("ix_mail_fetch_logs_trace_id", table_name="mail_fetch_logs")
    op.drop_table("mail_fetch_logs")

    op.drop_table("mail_account_claims")

    op.drop_index("ix_mail_accounts_owner_user_id", table_name="mail_accounts")
    op.drop_index("ix_mail_accounts_owner_type", table_name="mail_accounts")
    op.drop_index("ix_mail_accounts_email", table_name="mail_accounts")
    op.drop_table("mail_accounts")

    op.drop_index("ix_api_keys_key_prefix", table_name="api_keys")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
```

- [ ] **Step 7: Run tests and Alembic syntax check**

Run:

```bash
pytest tests/backend/test_database_metadata.py -v
python -m compileall backend
```

Expected: tests pass and compileall reports no syntax errors.

- [ ] **Step 8: Commit**

Run:

```bash
git add backend/app/db backend/app/models backend/migrations alembic.ini tests/backend/test_database_metadata.py
git commit -m "feat: add database foundation schema"
```

## Task 3: Single Docker Image With Internal Redis

**Files:**

- Create: `.env.example`
- Create: `Dockerfile`
- Create: `docker/entrypoint.sh`

- [ ] **Step 1: Add environment example**

Create `.env.example`:

```env
DATABASE_URL=postgresql+asyncpg://mailapi:change-me@db.example.com:5432/mailapi
REDIS_URL=redis://localhost:6379/0
RUN_MIGRATIONS=false
INIT_ADMIN_USERNAME=admin
INIT_ADMIN_PASSWORD=change-me-before-deploy
INIT_ADMIN_EMAIL=admin@example.com
SECRET_KEY=change-me
TOKEN_ENCRYPTION_KEY=change-me-32-byte-minimum
ACCESS_TOKEN_CACHE_TTL_SECONDS=3300
LOG_LEVEL=info
```

- [ ] **Step 2: Add Dockerfile**

Create `Dockerfile`:

```dockerfile
FROM node:22-bookworm AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends redis-server curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[dev]"

COPY backend ./backend
COPY alembic.ini ./alembic.ini
COPY docker/entrypoint.sh ./docker/entrypoint.sh
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

RUN chmod +x ./docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./docker/entrypoint.sh"]
```

- [ ] **Step 3: Add container entrypoint**

Create `docker/entrypoint.sh`:

```sh
#!/usr/bin/env sh
set -eu

redis-server --daemonize yes --bind 127.0.0.1 --port 6379

until redis-cli -h 127.0.0.1 -p 6379 ping | grep -q PONG; do
  sleep 0.2
done

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  alembic upgrade head
fi

exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

- [ ] **Step 4: Verify Docker-related syntax**

Run:

```bash
python -m compileall backend
```

Expected: no syntax errors.

If Docker is available locally, run:

```bash
docker build -t mailapi:phase1 .
```

Expected: image builds after the frontend shell exists. If Task 4 has not run yet, document that Docker build is blocked by missing `frontend/package.json`.

- [ ] **Step 5: Commit**

Run:

```bash
git add .env.example Dockerfile docker/entrypoint.sh
git commit -m "feat: add single-container docker runtime"
```

## Task 4: Vue Admin Shell

**Files:**

- Create: `frontend/index.html`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/env.d.ts`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/views/LoginView.vue`
- Create: `frontend/src/views/DashboardView.vue`

- [ ] **Step 1: Add frontend package**

Create `frontend/package.json`:

```json
{
  "name": "mailapi-web",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@element-plus/icons-vue": "^2.3.1",
    "element-plus": "^2.12.0",
    "pinia": "^3.0.4",
    "vue": "^3.5.25",
    "vue-router": "^4.6.3"
  },
  "devDependencies": {
    "@tsconfig/node22": "^22.0.0",
    "@vitejs/plugin-vue": "^6.0.2",
    "@vue/tsconfig": "^0.8.1",
    "typescript": "~5.9.0",
    "vite": "^7.2.4",
    "vue-tsc": "^3.1.5"
  }
}
```

- [ ] **Step 2: Add Vite and TypeScript config**

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>MailAPI</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

Create `frontend/vite.config.ts`:

```ts
import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
    },
  },
})
```

Create `frontend/tsconfig.json`:

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

Create `frontend/tsconfig.app.json`:

```json
{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "include": ["src/**/*", "src/**/*.vue"],
  "compilerOptions": {
    "composite": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

Create `frontend/tsconfig.node.json`:

```json
{
  "extends": "@tsconfig/node22/tsconfig.json",
  "include": ["vite.config.*"],
  "compilerOptions": {
    "composite": true,
    "noEmit": true
  }
}
```

- [ ] **Step 3: Add Vue shell**

Create `frontend/src/env.d.ts`:

```ts
/// <reference types="vite/client" />
```

Create `frontend/src/main.ts`:

```ts
import 'element-plus/dist/index.css'

import ElementPlus from 'element-plus'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'

createApp(App).use(createPinia()).use(router).use(ElementPlus).mount('#app')
```

Create `frontend/src/stores/auth.ts`:

```ts
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: '',
    username: '',
    role: 'user' as 'admin' | 'user',
  }),
  getters: {
    isAuthenticated: (state) => state.token.length > 0,
    isAdmin: (state) => state.role === 'admin',
  },
})
```

Create `frontend/src/router/index.ts`:

```ts
import { createRouter, createWebHistory } from 'vue-router'

import DashboardView from '@/views/DashboardView.vue'
import LoginView from '@/views/LoginView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView },
    { path: '/', name: 'dashboard', component: DashboardView },
  ],
})

export default router
```

Create `frontend/src/App.vue`:

```vue
<template>
  <RouterView />
</template>
```

Create `frontend/src/views/LoginView.vue`:

```vue
<template>
  <main class="login-page">
    <section class="login-panel">
      <h1>MailAPI</h1>
      <el-form label-position="top">
        <el-form-item label="用户名">
          <el-input placeholder="admin" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input type="password" show-password />
        </el-form-item>
        <el-button type="primary" class="login-button">登录</el-button>
      </el-form>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: #f6f8fb;
}

.login-panel {
  width: min(380px, calc(100vw - 32px));
  padding: 28px;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  background: #ffffff;
}

.login-button {
  width: 100%;
}
</style>
```

Create `frontend/src/views/DashboardView.vue`:

```vue
<template>
  <main class="dashboard">
    <header class="topbar">
      <h1>MailAPI 控制台</h1>
      <el-button>退出</el-button>
    </header>

    <section class="metrics">
      <article>
        <span>我的邮箱</span>
        <strong>0</strong>
      </article>
      <article>
        <span>公共池</span>
        <strong>0</strong>
      </article>
      <article>
        <span>今日取件</span>
        <strong>0</strong>
      </article>
      <article>
        <span>失败次数</span>
        <strong>0</strong>
      </article>
    </section>
  </main>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: #f6f8fb;
}

.topbar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid #d9e2ec;
  background: #ffffff;
}

.topbar h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  padding: 24px;
}

.metrics article {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  background: #ffffff;
}

.metrics span {
  color: #5c6b7a;
  font-size: 14px;
}

.metrics strong {
  color: #1f2933;
  font-size: 28px;
}
</style>
```

- [ ] **Step 4: Install and build frontend**

Run:

```bash
cd frontend
npm install
npm run build
```

Expected: `frontend/dist/index.html` exists and build exits with code 0.

- [ ] **Step 5: Commit**

Run:

```bash
git add frontend
git commit -m "feat: add vue admin shell"
```

## Task 5: Foundation Verification And Documentation

**Files:**

- Create: `README.md`
- Modify: `Agent.md`
- Modify: `docs/development-workflow.md`
- Modify: `docs/development-workflow.zh-CN.md`

- [ ] **Step 1: Add README**

Create `README.md`:

```md
# MailAPI

MailAPI 是一个面向 Outlook OAuth2 邮箱的验证码取件平台。

## 开发和部署约定

- **本机开发不使用 Docker**：直接启动 FastAPI 后端和 Vite 前端，方便调试。
- **最终部署再打包 Docker**：开发完成后，在服务器或有 Docker 的环境构建镜像；镜像内包含后端、前端静态文件和 Redis。
- **PostgreSQL 使用云端数据库**：本机开发和服务器部署都通过 `DATABASE_URL` 连接外部 PGSQL。

## 本机开发

安装后端依赖：

```bash
pip install -e ".[dev]"
```

准备环境变量：

```bash
copy .env.example .env
```

按实际情况修改 `.env` 里的 `DATABASE_URL`。第一阶段健康检查和基础测试不会连接真实数据库。

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

安装并启动前端：

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

打开：

- 后端健康检查：`http://127.0.0.1:8000/api/health`
- 前端开发服务：`http://127.0.0.1:5173/`

## 本机验证

后端测试：

```bash
pytest tests/backend -v
ruff check backend tests/backend
```

前端构建：

```bash
cd frontend
npm run build
```

Python 编译检查：

```bash
python -m compileall backend
```

## 服务器 Docker 部署

本机没有 Docker 时可以跳过这一节。等开发完成后，在服务器或有 Docker 的机器上执行：

```bash
docker build -t mailapi:latest .
docker run -d -p 8000:8000 --env-file .env --name mailapi mailapi:latest
```

打开：

- `http://服务器IP:8000/api/health`
- `http://服务器IP:8000/`
```

- [ ] **Step 2: Update `Agent.md` after task completion**

When all Phase 1 tasks are complete and user confirms, move task rows out of active tasks and archive task files under:

```text
docs/agent/archive/2026-06/
```

- [ ] **Step 3: Run full Phase 1 verification**

Run:

```bash
pytest tests/backend -v
ruff check backend tests/backend
cd frontend && npm run build
cd ..
python -m compileall backend
```

Docker is not required for local development. If Docker is available on this machine or a server, run:

```bash
docker build -t mailapi:phase1 .
```

Expected:

- Backend tests pass.
- Ruff reports no errors.
- Frontend build succeeds.
- Python compileall succeeds.
- Docker image builds when Docker is available; if Docker is not installed locally, record that Docker deployment verification was skipped and should be done on the server.

- [ ] **Step 4: Commit**

Run:

```bash
git add README.md Agent.md docs/development-workflow.md docs/development-workflow.zh-CN.md
git commit -m "docs: add phase 1 verification guide"
```

## Self-Review

Spec coverage for Phase 1:

- FastAPI backend foundation: Task 1.
- PostgreSQL/Alembic foundation: Task 2.
- Local non-Docker development workflow: Task 5.
- One Docker image with internal Redis for final server deployment: Task 3.
- Vue frontend shell served by backend: Task 4.
- Verification and handoff docs: Task 5.

Intentionally deferred to later plans:

- Login and JWT implementation.
- API Key lifecycle.
- Mailbox ownership services.
- Outlook OAuth2 Graph retrieval.
- IMAP XOAUTH2 fallback.
- Compatible mail APIs.
- Verification-code extraction.
- Logs and audit trails beyond schema.
