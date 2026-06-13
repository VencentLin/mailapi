# MailAPI Phase 2 Auth, Management, And Cloud DB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Phase 1 static console shell with a real login-gated management console backed by the cloud PostgreSQL configuration.

**Architecture:** Keep local development non-Docker. Backend adds DB connectivity checks, admin bootstrap, password hashing, JWT auth, `/auth/*`, and basic user management APIs. Frontend adds login submission, token storage, route guards, app layout, management navigation, and initial management pages.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, PostgreSQL/asyncpg, python-jose, pwdlib/argon2, pytest, Vue 3, Pinia, Vue Router, Element Plus.

---

## Root Cause Summary

Current behavior is expected from Phase 1, but it is not acceptable for the next usable milestone:

- `frontend/src/router/index.ts` maps `/` directly to `DashboardView`.
- `LoginView.vue` is static and does not call a backend login API.
- There is no route guard, so opening the app enters the console immediately.
- Backend only exposes `/api/health`; there is no `/auth/login`, `/auth/me`, or management API.
- `.env.example` contains placeholder database settings, and local `.env` must be configured with the user's cloud PostgreSQL connection string.

## Phase 2 Completion Criteria

- Opening `/` without a token redirects to `/login`.
- Login form calls `POST /auth/login`.
- Successful login stores a JWT and redirects to the management console.
- `GET /auth/me` returns the current user.
- Default admin can be created from environment variables.
- `DATABASE_URL` is documented and can be verified against cloud PostgreSQL.
- Alembic migrations can be run against the configured cloud database.
- Management console shows real navigation: Dashboard, Users, Mail Accounts, API Keys, Logs.
- User management page lists users from the database for admins.

## Task 1: Cloud PostgreSQL Configuration And Connectivity Check

**Files:**

- Modify: `.env.example`
- Modify: `README.md`
- Create: `backend/app/api/routes/health.py` update or extend
- Test: `tests/backend/test_health.py`

- [ ] **Step 1: Add DB health test**

Extend `tests/backend/test_health.py` with a DB health route test that can run without a real DB by monkeypatching the checker:

```python
@pytest.mark.asyncio
async def test_db_health_endpoint_reports_configured_database(monkeypatch):
    from backend.app.api.routes import health

    async def fake_check_database() -> dict[str, str]:
        return {"status": "ok", "database": "postgresql"}

    monkeypatch.setattr(health, "check_database", fake_check_database)

    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "postgresql"}
```

- [ ] **Step 2: Implement DB health check**

Update `backend/app/api/routes/health.py`:

```python
from sqlalchemy import text

from backend.app.db.session import AsyncSessionLocal


async def check_database() -> dict[str, str]:
    async with AsyncSessionLocal() as session:
        await session.execute(text("select 1"))
    return {"status": "ok", "database": "postgresql"}


@router.get("/health/db")
async def database_health() -> dict[str, str]:
    return await check_database()
```

- [ ] **Step 3: Update environment docs**

In `.env.example`, keep placeholders but make the cloud PostgreSQL format explicit:

```env
DATABASE_URL=postgresql+asyncpg://DB_USER:DB_PASSWORD@DB_HOST:5432/DB_NAME
RUN_MIGRATIONS=false
```

In `README.md`, add:

```md
## 配置云端 PostgreSQL

不要把真实数据库密码提交到 git。复制 `.env.example` 为 `.env`，然后填写：

```env
DATABASE_URL=postgresql+asyncpg://用户名:密码@主机:5432/数据库名
```

验证数据库连接：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000/api/health/db`。

执行迁移：

```bash
alembic upgrade head
```
```

- [ ] **Step 4: Verify**

Run:

```bash
pytest tests/backend/test_health.py -v
ruff check backend tests/backend
```

Expected: tests pass and lint passes.

If real cloud DB credentials are available in `.env`, also run:

```bash
alembic upgrade head
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open `/api/health/db`.

If credentials are not available, mark the real DB check as blocked and ask the user for `DATABASE_URL`.

## Task 2: Backend Auth And Admin Bootstrap

**Files:**

- Create: `backend/app/core/security.py`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/api/routes/auth.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/services/users.py`
- Create: `backend/app/cli.py`
- Modify: `pyproject.toml`
- Test: `tests/backend/test_auth.py`

- [ ] **Step 1: Write auth tests**

Create tests for:

- Password hashing verifies correct password and rejects wrong password.
- Login returns an access token for an active user.
- `/auth/me` returns current user when token is valid.
- Disabled users cannot login.

Use an isolated SQLite async test database or dependency override for `get_db_session`.

- [ ] **Step 2: Add auth dependencies and settings**

Add these dependencies to `pyproject.toml`:

```toml
"pwdlib[argon2]>=0.2.1",
```

Add this dev dependency if tests need an isolated async SQLite database:

```toml
"aiosqlite>=0.20.0",
```

Add settings to `backend/app/core/config.py`:

```python
secret_key: str = "change-me"
access_token_expire_minutes: int = 60 * 24
```

- [ ] **Step 3: Add security helpers**

`backend/app/core/security.py` should expose:

```python
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from pwdlib import PasswordHash

from backend.app.core.config import get_settings

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, password_hash_value: str) -> bool:
    return password_hash.verify(password, password_hash_value)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expire_delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    expire_at = datetime.now(UTC) + expire_delta
    payload: dict[str, Any] = {"sub": subject, "exp": expire_at}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid access token") from exc
```

- [ ] **Step 4: Add auth schemas and routes**

Implement:

- `POST /auth/login`
- `GET /auth/me`

Login request:

```json
{"username": "admin", "password": "password"}
```

Login response:

```json
{"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example", "token_type": "bearer"}
```

- [ ] **Step 5: Add admin bootstrap command**

Add a CLI command callable as:

```bash
python -m backend.app.cli create-admin
```

It should read:

- `INIT_ADMIN_USERNAME`
- `INIT_ADMIN_PASSWORD`
- `INIT_ADMIN_EMAIL`

If admin exists, print a clear message and do not duplicate it.

- [ ] **Step 6: Verify**

Run:

```bash
pytest tests/backend/test_auth.py -v
pytest tests/backend -v
ruff check backend tests/backend
python -m compileall backend
```

Expected: all pass.

## Task 3: Frontend Login Flow And Route Guard

**Files:**

- Modify: `frontend/src/stores/auth.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/LoginView.vue`
- Create: `frontend/src/api/http.ts`
- Create: `frontend/src/api/auth.ts`

- [ ] **Step 1: Add API helpers**

Create a small fetch wrapper that adds `Authorization: Bearer <token>` when token exists and throws readable errors for non-2xx responses.

- [ ] **Step 2: Update Pinia auth store**

Store:

- `accessToken`
- `user`
- `login(username, password)`
- `loadMe()`
- `logout()`

Persist token in `localStorage`.

- [ ] **Step 3: Add route guard**

Rules:

- `/login` is public.
- `/` and management routes require token.
- Opening `/` without token redirects to `/login`.
- Opening `/login` with valid token redirects to `/`.

- [ ] **Step 4: Wire login page**

Login form should:

- Bind username/password.
- Show loading state.
- Call store `login`.
- Redirect to `/` on success.
- Show backend error on failure.

- [ ] **Step 5: Verify**

Run:

```bash
cd frontend
npm run build
```

Manual check:

- Open `/`, expect redirect to `/login`.
- Login with valid admin after backend Task 2 is complete.
- Refresh page, token persists.
- Click logout, token clears and app returns to `/login`.

## Task 4: Management Layout And Navigation

**Files:**

- Create: `frontend/src/layouts/AppLayout.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/DashboardView.vue`
- Create: `frontend/src/views/users/UserListView.vue`
- Create: `frontend/src/views/mail/MailAccountListView.vue`
- Create: `frontend/src/views/apiKeys/ApiKeyListView.vue`
- Create: `frontend/src/views/logs/MailFetchLogView.vue`

- [ ] **Step 1: Add layout**

Create a management layout with:

- Top bar.
- Left menu.
- Logout button.
- Router outlet.

Menu items:

- 工作台
- 用户管理
- 邮箱管理
- API Key
- 取件日志

- [ ] **Step 2: Add routes**

Add child routes under the authenticated layout:

- `/`
- `/users`
- `/mail-accounts`
- `/api-keys`
- `/logs/mail-fetch`

- [ ] **Step 3: Add placeholder management pages**

Each page should clearly show its module title and empty state. This makes management visible even before all business APIs are complete.

- [ ] **Step 4: Verify**

Run:

```bash
cd frontend
npm run build
```

Manual check after login:

- Sidebar appears.
- Each menu item navigates to its page.
- Logout returns to login.

## Task 5: Admin User Management API And Page

**Files:**

- Create: `backend/app/api/routes/users.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/app/schemas/users.py`
- Extend: `backend/app/services/users.py`
- Test: `tests/backend/test_users_api.py`
- Modify: `frontend/src/views/users/UserListView.vue`
- Create: `frontend/src/api/users.ts`

- [ ] **Step 1: Add backend tests**

Cover:

- Admin can list users.
- Ordinary user cannot list users.
- Admin can create a user.
- Duplicate username/email returns a structured error.

- [ ] **Step 2: Implement backend routes**

Routes:

- `GET /users`
- `POST /users`

Require admin role.

- [ ] **Step 3: Implement frontend user list**

The users page should:

- Call `GET /users`.
- Show username, email, role, status, created time.
- Provide a create-user dialog with username/email/password/role.
- Refresh list after creation.

- [ ] **Step 4: Verify**

Run:

```bash
pytest tests/backend/test_users_api.py -v
pytest tests/backend -v
ruff check backend tests/backend
cd frontend && npm run build
```

Manual check:

- Login as admin.
- Open 用户管理.
- Create a user.
- See the new user in the list.

## Notes For Cloud Database Credentials

Do not commit `.env`.

The user must provide either:

```text
DATABASE_URL=postgresql+asyncpg://用户名:密码@主机:5432/数据库名
```

or these fields:

- host
- port
- database name
- username
- password

If credentials are not available, Claude should still complete code and tests, then mark cloud DB verification as blocked with a clear note.
