from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.enums import UserRole
from backend.app.models.logs import MailFetchLog
from backend.app.services.users import create_user


async def _login_as(
    client: AsyncClient,
    session: AsyncSession,
    username: str,
    role: UserRole,
) -> tuple[int, str]:
    user = await create_user(
        session,
        username=username,
        email=f"{username}@example.com",
        password="pw",
        role=role,
    )
    resp = await client.post("/auth/login", json={"username": username, "password": "pw"})
    assert resp.status_code == 200
    return user.id, resp.json()["access_token"]


async def _create_fetch_log(
    session: AsyncSession,
    *,
    user_id: int | None,
    email: str,
    status: str,
) -> None:
    session.add(
        MailFetchLog(
            trace_id=f"trace-{email}",
            user_id=user_id,
            api_key_id=None,
            mail_account_id=None,
            email=email,
            mailbox="INBOX",
            operation="mail_new",
            source_protocol="graph",
            status=status,
            duration_ms=12,
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_admin_can_list_and_filter_mail_fetch_logs(
    client: AsyncClient,
    test_session: AsyncSession,
):
    _, admin_token = await _login_as(client, test_session, "logsadmin", UserRole.ADMIN)
    user_id, _ = await _login_as(client, test_session, "logsuser", UserRole.USER)
    await _create_fetch_log(
        test_session,
        user_id=user_id,
        email="success@example.com",
        status="success",
    )
    await _create_fetch_log(
        test_session,
        user_id=None,
        email="failed@example.com",
        status="failed",
    )

    resp = await client.get(
        "/api/logs/mail-fetch?status=failed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert [item["email"] for item in body] == ["failed@example.com"]


@pytest.mark.asyncio
async def test_regular_user_lists_only_own_mail_fetch_logs(
    client: AsyncClient,
    test_session: AsyncSession,
):
    owner_id, owner_token = await _login_as(client, test_session, "logsowner", UserRole.USER)
    other_id, _ = await _login_as(client, test_session, "logsother", UserRole.USER)
    await _create_fetch_log(
        test_session,
        user_id=owner_id,
        email="mine@example.com",
        status="success",
    )
    await _create_fetch_log(
        test_session,
        user_id=other_id,
        email="other@example.com",
        status="success",
    )

    resp = await client.get(
        "/api/logs/mail-fetch",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert resp.status_code == 200
    assert [item["email"] for item in resp.json()] == ["mine@example.com"]
