from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.enums import UserRole, UserStatus
from backend.app.services.users import create_user

# ---------------------------------------------------------------------------
# helpers (fixtures are in conftest.py)
# ---------------------------------------------------------------------------


async def login_as(
    client: AsyncClient, test_session: AsyncSession, username: str, role: UserRole
) -> str:
    """Create a user with the given role and return a bearer token."""
    await create_user(
        test_session,
        username=username,
        email=f"{username}@example.com",
        password="pw",
        role=role,
        status=UserStatus.ACTIVE,
    )
    resp = await client.post(
        "/auth/login", json={"username": username, "password": "pw"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# GET /api/users
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_list_users(client, test_session):
    token = await login_as(client, test_session, "admin1", UserRole.ADMIN)

    # Create another user so the list is non-empty
    await create_user(
        test_session,
        username="regular",
        email="regular@example.com",
        password="pw",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )

    resp = await client.get(
        "/api/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    usernames = {u["username"] for u in body}
    assert "regular" in usernames


@pytest.mark.asyncio
async def test_regular_user_cannot_list_users(client, test_session):
    token = await login_as(client, test_session, "regular2", UserRole.USER)

    resp = await client.get(
        "/api/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_users_respects_limit(client, test_session):
    token = await login_as(client, test_session, "admin2", UserRole.ADMIN)

    for i in range(5):
        await create_user(
            test_session,
            username=f"user{i}",
            email=f"user{i}@example.com",
            password="pw",
            role=UserRole.USER,
        )

    resp = await client.get(
        "/api/users?limit=3", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3


@pytest.mark.asyncio
async def test_list_users_requires_auth(client):
    resp = await client.get("/api/users")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/users
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_create_user(client, test_session):
    token = await login_as(client, test_session, "admin3", UserRole.ADMIN)

    resp = await client.post(
        "/api/users",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "secret123",
            "role": "user",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "newuser"
    assert body["email"] == "newuser@example.com"
    assert body["role"] == "user"
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_username(client, test_session):
    token = await login_as(client, test_session, "admin4", UserRole.ADMIN)

    await create_user(
        test_session,
        username="dup",
        email="dup1@example.com",
        password="pw",
        role=UserRole.USER,
    )

    resp = await client.post(
        "/api/users",
        json={
            "username": "dup",
            "email": "dup2@example.com",
            "password": "secret123",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_email(client, test_session):
    token = await login_as(client, test_session, "admin5", UserRole.ADMIN)

    await create_user(
        test_session,
        username="unique1",
        email="dup@example.com",
        password="pw",
        role=UserRole.USER,
    )

    resp = await client.post(
        "/api/users",
        json={
            "username": "unique2",
            "email": "dup@example.com",
            "password": "secret123",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_regular_user_cannot_create_user(client, test_session):
    token = await login_as(client, test_session, "regular3", UserRole.USER)

    resp = await client.post(
        "/api/users",
        json={
            "username": "hacker",
            "email": "hacker@example.com",
            "password": "secret123",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/users/{user_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_edit_user_and_activate_pending_registration(client, test_session):
    admin_token = await login_as(client, test_session, "admin6", UserRole.ADMIN)
    pending = await create_user(
        test_session,
        username="pending-edit",
        email="pending-edit@example.com",
        password="oldpass",
        role=UserRole.USER,
        status=UserStatus.DISABLED,
    )

    resp = await client.patch(
        f"/api/users/{pending.id}",
        json={
            "username": "active-edit",
            "email": "active-edit@example.com",
            "role": "user",
            "status": "active",
            "password": "newpass123",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "active-edit"
    assert body["email"] == "active-edit@example.com"
    assert body["role"] == "user"
    assert body["status"] == "active"

    login_resp = await client.post(
        "/auth/login",
        json={"username": "active-edit", "password": "newpass123"},
    )
    assert login_resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_disable_user_account(client, test_session):
    admin_token = await login_as(client, test_session, "admin7", UserRole.ADMIN)
    target = await create_user(
        test_session,
        username="target-disable",
        email="target-disable@example.com",
        password="pw",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )

    resp = await client.patch(
        f"/api/users/{target.id}",
        json={"status": "disabled"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"

    login_resp = await client.post(
        "/auth/login",
        json={"username": "target-disable", "password": "pw"},
    )
    assert login_resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_cannot_disable_or_demote_self(client, test_session):
    admin_token = await login_as(client, test_session, "admin8", UserRole.ADMIN)
    users_resp = await client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    admin_id = next(
        user["id"] for user in users_resp.json() if user["username"] == "admin8"
    )

    disable_resp = await client.patch(
        f"/api/users/{admin_id}",
        json={"status": "disabled"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert disable_resp.status_code == 400

    demote_resp = await client.patch(
        f"/api/users/{admin_id}",
        json={"role": "user"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert demote_resp.status_code == 400


@pytest.mark.asyncio
async def test_regular_user_cannot_edit_users(client, test_session):
    token = await login_as(client, test_session, "regular4", UserRole.USER)
    target = await create_user(
        test_session,
        username="regular-target",
        email="regular-target@example.com",
        password="pw",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )

    resp = await client.patch(
        f"/api/users/{target.id}",
        json={"status": "disabled"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
