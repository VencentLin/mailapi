from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.api_key import ApiKey
from backend.app.models.enums import (
    ApiKeyStatus,
    MailAccountOwnerType,
    MailAccountStatus,
    UserRole,
    UserStatus,
)
from backend.app.models.logs import AuditLog, MailAccountClaim, MailFetchLog
from backend.app.models.mail_account import MailAccount
from backend.app.models.user import User
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


# ---------------------------------------------------------------------------
# DELETE /api/users/{user_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_delete_user_and_cleanup_related_records(client, test_session):
    admin_token = await login_as(client, test_session, "admin9", UserRole.ADMIN)
    target = await create_user(
        test_session,
        username="delete-target",
        email="delete-target@example.com",
        password="pw",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    api_key = ApiKey(
        user_id=target.id,
        name="delete-key",
        key_prefix="delete-key",
        key_hash="hash",
        scopes=[],
        status=ApiKeyStatus.ACTIVE,
    )
    account = MailAccount(
        email="delete-owned@example.com",
        client_id="client",
        refresh_token_encrypted="encrypted",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=target.id,
        status=MailAccountStatus.ACTIVE,
        created_by_user_id=target.id,
        created_via="test",
    )
    test_session.add_all([api_key, account])
    await test_session.commit()
    await test_session.refresh(api_key)
    await test_session.refresh(account)

    test_session.add_all(
        [
            MailFetchLog(
                trace_id="delete-trace",
                user_id=target.id,
                api_key_id=api_key.id,
                mail_account_id=account.id,
                email=account.email,
                mailbox="INBOX",
                operation="fetch",
                status="success",
                duration_ms=12,
            ),
            MailAccountClaim(
                mail_account_id=account.id,
                claimed_by_user_id=target.id,
                previous_owner_type="public",
            ),
            AuditLog(
                actor_user_id=target.id,
                action="user.delete.test",
                target_type="user",
                target_id=str(target.id),
                metadata_json={},
            ),
        ]
    )
    await test_session.commit()

    resp = await client.delete(
        f"/api/users/{target.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 204
    assert await test_session.get(User, target.id) is None
    assert await test_session.get(ApiKey, api_key.id) is None

    refreshed_account = await test_session.get(MailAccount, account.id)
    assert refreshed_account is not None
    assert refreshed_account.owner_type == MailAccountOwnerType.PUBLIC
    assert refreshed_account.owner_user_id is None
    assert refreshed_account.created_by_user_id is None

    fetch_log = (
        await test_session.execute(
            select(MailFetchLog).where(MailFetchLog.trace_id == "delete-trace")
        )
    ).scalar_one()
    assert fetch_log.user_id is None
    assert fetch_log.api_key_id is None

    audit_log = (
        await test_session.execute(
            select(AuditLog).where(AuditLog.action == "user.delete.test")
        )
    ).scalar_one()
    assert audit_log.actor_user_id is None

    claims = (
        await test_session.execute(
            select(MailAccountClaim).where(
                MailAccountClaim.claimed_by_user_id == target.id
            )
        )
    ).scalars().all()
    assert claims == []


@pytest.mark.asyncio
async def test_admin_cannot_delete_self(client, test_session):
    admin_token = await login_as(client, test_session, "admin10", UserRole.ADMIN)
    users_resp = await client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    admin_id = next(
        user["id"] for user in users_resp.json() if user["username"] == "admin10"
    )

    resp = await client.delete(
        f"/api/users/{admin_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_regular_user_cannot_delete_users(client, test_session):
    token = await login_as(client, test_session, "regular5", UserRole.USER)
    target = await create_user(
        test_session,
        username="regular-delete-target",
        email="regular-delete-target@example.com",
        password="pw",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )

    resp = await client.delete(
        f"/api/users/{target.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403
