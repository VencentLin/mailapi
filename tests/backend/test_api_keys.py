from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.api_key import ApiKey
from backend.app.models.enums import ApiKeyStatus, MailAccountOwnerType, UserRole
from backend.app.models.logs import MailFetchLog
from backend.app.models.mail_account import MailAccount
from backend.app.services.users import create_user


async def _login_as(
    client: AsyncClient,
    session: AsyncSession,
    username: str,
    role: UserRole,
) -> str:
    await create_user(
        session,
        username=username,
        email=f"{username}@example.com",
        password="pw",
        role=role,
    )
    resp = await client.post("/auth/login", json={"username": username, "password": "pw"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_user_can_create_api_key_and_plaintext_is_not_stored(
    client: AsyncClient,
    test_session: AsyncSession,
):
    token = await _login_as(client, test_session, "keyuser", UserRole.USER)

    resp = await client.post(
        "/api/api-keys",
        json={"name": "fetch script", "scopes": ["mail:fetch"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["api_key"].startswith("mailapi_")
    assert body["key"]["name"] == "fetch script"
    assert body["key"]["key_prefix"] == body["api_key"][:16]

    stored = (await test_session.execute(select(ApiKey))).scalar_one()
    assert stored.key_hash != body["api_key"]
    assert body["api_key"] not in stored.key_hash


@pytest.mark.asyncio
async def test_regular_user_lists_only_own_api_keys(
    client: AsyncClient,
    test_session: AsyncSession,
):
    first_token = await _login_as(client, test_session, "keyowner1", UserRole.USER)
    second_token = await _login_as(client, test_session, "keyowner2", UserRole.USER)

    await client.post(
        "/api/api-keys",
        json={"name": "mine"},
        headers={"Authorization": f"Bearer {first_token}"},
    )
    await client.post(
        "/api/api-keys",
        json={"name": "other"},
        headers={"Authorization": f"Bearer {second_token}"},
    )

    resp = await client.get(
        "/api/api-keys",
        headers={"Authorization": f"Bearer {first_token}"},
    )

    assert resp.status_code == 200
    names = [item["name"] for item in resp.json()]
    assert names == ["mine"]


@pytest.mark.asyncio
async def test_admin_can_create_key_for_user_and_disable_it(
    client: AsyncClient,
    test_session: AsyncSession,
):
    admin_token = await _login_as(client, test_session, "keyadmin", UserRole.ADMIN)
    user = await create_user(
        test_session,
        username="targetuser",
        email="target@example.com",
        password="pw",
        role=UserRole.USER,
    )

    create_resp = await client.post(
        "/api/api-keys",
        json={"name": "target key", "user_id": user.id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    key_id = create_resp.json()["key"]["id"]

    delete_resp = await client.delete(
        f"/api/api-keys/{key_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_resp.status_code == 204

    stored = await test_session.get(ApiKey, key_id)
    assert stored is not None
    assert stored.status == ApiKeyStatus.DISABLED


@pytest.mark.asyncio
async def test_expired_api_key_cannot_be_used_for_compatible_fetch(
    client: AsyncClient,
    test_session: AsyncSession,
):
    token = await _login_as(client, test_session, "expiredowner", UserRole.USER)
    create_resp = await client.post(
        "/api/api-keys",
        json={
            "name": "expired",
            "expires_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_resp.json()["api_key"]

    resp = await client.post(
        "/api/mail_new",
        json={
            "email": "expired@outlook.com",
            "client_id": "cid",
            "refresh_token": "rt",
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert resp.status_code == 401
    assert resp.json()["error_code"] == "API_KEY_EXPIRED"


@pytest.mark.asyncio
async def test_compatible_fetch_with_api_key_creates_user_owned_mailbox_and_logs_api_key(
    client: AsyncClient,
    test_session: AsyncSession,
):
    token = await _login_as(client, test_session, "fetchkeyowner", UserRole.USER)
    create_resp = await client.post(
        "/api/api-keys",
        json={"name": "fetch key", "scopes": ["mail:fetch"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_resp.json()["api_key"]
    api_key_id = create_resp.json()["key"]["id"]

    with patch(
        "backend.app.api.routes.mail.fetch_messages",
        new=AsyncMock(return_value=([], "graph")),
    ):
        resp = await client.post(
            "/api/mail_new",
            json={
                "email": "apikey-owned@outlook.com",
                "client_id": "cid",
                "refresh_token": "rt",
            },
            headers={"Authorization": f"Bearer {api_key}"},
        )

    assert resp.status_code == 200
    assert resp.json()["mail_account_status"] == "auto_created_user"

    account = (
        await test_session.execute(
            select(MailAccount).where(MailAccount.email == "apikey-owned@outlook.com")
        )
    ).scalar_one()
    assert account.owner_type == MailAccountOwnerType.USER

    log = (await test_session.execute(select(MailFetchLog))).scalar_one()
    assert log.api_key_id == api_key_id


@pytest.mark.asyncio
async def test_compatible_fetch_accepts_body_user_token(
    client: AsyncClient,
    test_session: AsyncSession,
):
    token = await _login_as(client, test_session, "bodytokenowner", UserRole.USER)
    create_resp = await client.post(
        "/api/api-keys",
        json={"name": "body token"},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = create_resp.json()["api_key"]

    with patch(
        "backend.app.api.routes.mail.fetch_messages",
        new=AsyncMock(return_value=([], "imap")),
    ):
        resp = await client.post(
            "/api/mail_all",
            json={
                "email": "body-token@outlook.com",
                "client_id": "cid",
                "refresh_token": "rt",
                "user_token": api_key,
            },
        )

    assert resp.status_code == 200
    assert resp.json()["mail_account_status"] == "auto_created_user"
    assert resp.json()["protocol"] == "imap"
