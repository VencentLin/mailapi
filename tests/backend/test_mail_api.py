"""Tests for the compatible mail fetch API endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.crypto import TokenCipher
from backend.app.models.enums import MailAccountOwnerType, MailAccountStatus, UserRole
from backend.app.models.logs import MailFetchLog
from backend.app.models.mail_account import MailAccount
from backend.app.services.mail_fetchers import MailFetchResult
from backend.app.services.users import create_user


async def _create_account(session: AsyncSession, email: str, token: str, cipher: TokenCipher):
    account = MailAccount(
        email=email,
        client_id="cid",
        refresh_token_encrypted=cipher.encrypt(token),
        owner_type=MailAccountOwnerType.USER,
        status=MailAccountStatus.ACTIVE,
        created_via="api",
    )
    session.add(account)
    await session.commit()


# ---------------------------------------------------------------------------
# POST /api/mail/fetch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_authenticated_with_token_creates_and_fetches(
    client: AsyncClient, test_session: AsyncSession
):
    """User provides token → account is created/retrieved → mail fetched."""
    await create_user(
        test_session,
        username="fetcher",
        email="fetcher@example.com",
        password="pw",
        role=UserRole.USER,
    )
    login_resp = await client.post(
        "/auth/login", json={"username": "fetcher", "password": "pw"}
    )
    token = login_resp.json()["access_token"]

    with patch(
        "backend.app.api.routes.mail.fetch_mail_for_account",
        new=AsyncMock(
            return_value=MailFetchResult(
                success=True, message_count=3, provider="graph"
            )
        ),
    ):
        resp = await client.post(
            "/api/mail/fetch",
            json={
                "email": "my@outlook.com",
                "client_id": "cid-123",
                "refresh_token": "rt-secret",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["message_count"] == 3
    assert body["provider"] == "graph"


@pytest.mark.asyncio
async def test_fetch_anonymous_creates_public_and_fetches(
    client: AsyncClient, test_session: AsyncSession
):
    """No auth → public account created → mail fetched."""
    with patch(
        "backend.app.api.routes.mail.fetch_mail_for_account",
        new=AsyncMock(
            return_value=MailFetchResult(
                success=True, message_count=1, provider="graph"
            )
        ),
    ):
        resp = await client.post(
            "/api/mail/fetch",
            json={
                "email": "public@outlook.com",
                "client_id": "cid-pub",
                "refresh_token": "rt-pub",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["message_count"] == 1


@pytest.mark.asyncio
async def test_fetch_missing_email_returns_422(client: AsyncClient):
    """Email is required."""
    resp = await client.post("/api/mail/fetch", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_fetch_new_account_missing_credentials_returns_400(
    client: AsyncClient, test_session: AsyncSession
):
    """New email with empty client_id → 400 error."""
    await create_user(
        test_session,
        username="badreq",
        email="badreq@example.com",
        password="pw",
        role=UserRole.USER,
    )
    login_resp = await client.post(
        "/auth/login", json={"username": "badreq", "password": "pw"}
    )
    token = login_resp.json()["access_token"]

    resp = await client.post(
        "/api/mail/fetch",
        json={
            "email": "new@outlook.com",
            "client_id": "",
            "refresh_token": "rt",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "client_id" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_fetch_existing_account_no_new_credentials_needed(
    client: AsyncClient, test_session: AsyncSession
):
    """Existing account → fetch with stored credentials (no new tokens needed)."""
    cipher = TokenCipher(key=get_settings().token_encryption_key)
    await _create_account(test_session, "existing@outlook.com", "stored-rt", cipher)

    await create_user(
        test_session,
        username="existinguser",
        email="eu@example.com",
        password="pw",
        role=UserRole.USER,
    )
    login_resp = await client.post(
        "/auth/login", json={"username": "existinguser", "password": "pw"}
    )
    token = login_resp.json()["access_token"]

    with patch(
        "backend.app.api.routes.mail.fetch_mail_for_account",
        new=AsyncMock(
            return_value=MailFetchResult(
                success=True, message_count=2, provider="graph"
            )
        ),
    ):
        resp = await client.post(
            "/api/mail/fetch",
            json={"email": "existing@outlook.com"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


# ---------------------------------------------------------------------------
# Legacy compatible endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mail_new_auto_creates_public_mailbox_and_returns_envelope(
    client: AsyncClient, test_session: AsyncSession
):
    with patch(
        "backend.app.api.routes.mail.fetch_messages",
        new=AsyncMock(
            return_value=(
                [
                    {
                        "id": "m1",
                        "sender": "sender@example.com",
                        "subject": "Code",
                        "text": "Your code is 123456",
                        "html": "<p>Your code is 123456</p>",
                        "received_at": "2026-06-13T01:00:00Z",
                    }
                ],
                "graph",
            )
        ),
    ):
        resp = await client.post(
            "/api/mail_new",
            json={
                "email": "public2@outlook.com",
                "client_id": "cid-pub",
                "refresh_token": "rt-pub",
                "mailbox": "INBOX",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "200"
    assert body["protocol"] == "graph"
    assert body["mail_account_status"] == "auto_created_public"
    assert body["data"][0]["subject"] == "Code"
    assert body["data"][0]["verification_code"] == "123456"
    assert body["trace_id"]

    logs = (await test_session.execute(select(MailFetchLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].operation == "mail_new"
    assert logs[0].status == "success"
    assert logs[0].source_protocol == "graph"


@pytest.mark.asyncio
async def test_mail_all_get_supports_authenticated_user_owned_mailbox(
    client: AsyncClient, test_session: AsyncSession
):
    await create_user(
        test_session,
        username="legacyuser",
        email="legacyuser@example.com",
        password="pw",
        role=UserRole.USER,
    )
    login_resp = await client.post(
        "/auth/login", json={"username": "legacyuser", "password": "pw"}
    )
    token = login_resp.json()["access_token"]

    with patch(
        "backend.app.api.routes.mail.fetch_messages",
        new=AsyncMock(return_value=([], "imap")),
    ):
        resp = await client.get(
            "/api/mail_all",
            params={
                "email": "owned@outlook.com",
                "client_id": "cid-owned",
                "refresh_token": "rt-owned",
                "mailbox": "Junk",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "200"
    assert body["protocol"] == "imap"
    assert body["mail_account_status"] == "auto_created_user"
    assert body["data"] == []


@pytest.mark.asyncio
async def test_mail_new_existing_account_allows_missing_credentials(
    client: AsyncClient, test_session: AsyncSession
):
    cipher = TokenCipher(key=get_settings().token_encryption_key)
    await _create_account(test_session, "legacy-existing@outlook.com", "stored-rt", cipher)

    with patch(
        "backend.app.api.routes.mail.fetch_messages",
        new=AsyncMock(return_value=([], "graph")),
    ):
        resp = await client.post(
            "/api/mail_new",
            json={"email": "legacy-existing@outlook.com", "mailbox": "INBOX"},
        )

    assert resp.status_code == 200
    assert resp.json()["mail_account_status"] == "existing_user"


@pytest.mark.asyncio
async def test_mail_new_failure_writes_failed_log(
    client: AsyncClient, test_session: AsyncSession
):
    with patch(
        "backend.app.api.routes.mail.fetch_messages",
        new=AsyncMock(side_effect=RuntimeError("fetch failed")),
    ):
        resp = await client.post(
            "/api/mail_new",
            json={
                "email": "failure@outlook.com",
                "client_id": "cid",
                "refresh_token": "rt",
                "mailbox": "INBOX",
            },
        )

    assert resp.status_code == 502
    body = resp.json()
    assert body["code"] == "502"
    assert body["trace_id"]

    logs = (await test_session.execute(select(MailFetchLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].operation == "mail_new"
    assert logs[0].status == "failed"
    assert logs[0].error_code == "mail_fetch_failed"


@pytest.mark.asyncio
async def test_process_mailbox_calls_clear_and_logs_success(
    client: AsyncClient, test_session: AsyncSession
):
    with patch(
        "backend.app.api.routes.mail.clear_mailbox",
        new=AsyncMock(return_value="graph"),
    ):
        resp = await client.post(
            "/api/process-mailbox",
            json={
                "email": "clear@outlook.com",
                "client_id": "cid",
                "refresh_token": "rt",
                "mailbox": "INBOX",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "200"
    assert body["protocol"] == "graph"
    assert body["data"]["message"]

    logs = (await test_session.execute(select(MailFetchLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].operation == "process_mailbox"
    assert logs[0].status == "success"
