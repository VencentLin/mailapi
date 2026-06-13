from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.crypto import TokenCipher
from backend.app.models.api_key import ApiKey
from backend.app.models.enums import ApiKeyStatus, MailAccountOwnerType, MailAccountStatus, UserRole
from backend.app.models.logs import MailFetchLog
from backend.app.models.mail_account import MailAccount
from backend.app.services.api_keys import hash_api_key
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


async def _create_mail_account(
    session: AsyncSession,
    *,
    email: str,
    owner_type: MailAccountOwnerType,
    owner_user_id: int | None = None,
) -> None:
    cipher = TokenCipher(key=get_settings().token_encryption_key)
    session.add(
        MailAccount(
            email=email,
            client_id="client-id",
            refresh_token_encrypted=cipher.encrypt("refresh-token"),
            owner_type=owner_type,
            owner_user_id=owner_user_id,
            status=MailAccountStatus.ACTIVE,
            created_via="test",
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_verification_code_extracts_default_code_and_logs_success(
    client: AsyncClient,
    test_session: AsyncSession,
):
    with patch(
        "backend.app.api.routes.mail.fetch_messages",
        new=AsyncMock(
            return_value=(
                [
                    {
                        "id": "m1",
                        "sender": "noreply@example.com",
                        "subject": "Your login code",
                        "text": "Use 654321 to continue",
                        "received_at": "2026-06-13T01:00:00Z",
                    }
                ],
                "graph",
            )
        ),
    ):
        resp = await client.post(
            "/api/verification-code",
            json={
                "email": "verify-public@example.com",
                "client_id": "cid",
                "refresh_token": "rt",
                "sender": "noreply",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_code"] == "654321"
    assert body["source_protocol"] == "graph"
    assert body["mail_account_status"] == "auto_created_public"
    assert body["matched_email"]["id"] == "m1"

    logs = (await test_session.execute(MailFetchLog.__table__.select())).all()
    assert len(logs) == 1
    assert logs[0]._mapping["operation"] == "verification_code"
    assert logs[0]._mapping["status"] == "success"


@pytest.mark.asyncio
async def test_verification_code_returns_not_found_when_filters_do_not_match(
    client: AsyncClient,
):
    with patch(
        "backend.app.api.routes.mail.fetch_messages",
        new=AsyncMock(
            return_value=(
                [
                    {
                        "id": "m1",
                        "sender": "other@example.com",
                        "subject": "No match",
                        "text": "Use 123456",
                        "received_at": "2026-06-13T01:00:00Z",
                    }
                ],
                "imap",
            )
        ),
    ):
        resp = await client.post(
            "/api/verification-code",
            json={
                "email": "verify-miss@example.com",
                "client_id": "cid",
                "refresh_token": "rt",
                "sender": "noreply",
            },
        )

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "VERIFICATION_CODE_NOT_FOUND"


@pytest.mark.asyncio
async def test_dashboard_metrics_are_scoped_by_role(
    client: AsyncClient,
    test_session: AsyncSession,
):
    owner_id, owner_token = await _login_as(client, test_session, "dashowner", UserRole.USER)
    other_id, _ = await _login_as(client, test_session, "dashother", UserRole.USER)
    _, admin_token = await _login_as(client, test_session, "dashadmin", UserRole.ADMIN)
    await _create_mail_account(
        test_session,
        email="owner@example.com",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=owner_id,
    )
    await _create_mail_account(
        test_session,
        email="other@example.com",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=other_id,
    )
    await _create_mail_account(
        test_session,
        email="public-dash@example.com",
        owner_type=MailAccountOwnerType.PUBLIC,
    )
    session_key = ApiKey(
        user_id=owner_id,
        name="dash",
        key_prefix="mailapi_dash_key",
        key_hash=hash_api_key("mailapi_dash_key_value"),
        scopes=[],
        status=ApiKeyStatus.ACTIVE,
    )
    test_session.add(session_key)
    test_session.add(
        MailFetchLog(
            trace_id="dash-trace",
            user_id=owner_id,
            api_key_id=None,
            mail_account_id=None,
            email="owner@example.com",
            mailbox="INBOX",
            operation="mail_new",
            source_protocol="graph",
            status="failed",
            duration_ms=50,
        )
    )
    await test_session.commit()

    user_resp = await client.get(
        "/api/dashboard",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    admin_resp = await client.get(
        "/api/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert user_resp.status_code == 200
    assert user_resp.json()["my_mail_accounts"] == 1
    assert user_resp.json()["public_mail_accounts"] == 1
    assert user_resp.json()["today_failed_fetches"] == 1

    assert admin_resp.status_code == 200
    assert admin_resp.json()["global_users"] == 3
    assert admin_resp.json()["global_mail_accounts"] == 3
    assert admin_resp.json()["global_api_keys"] == 1
