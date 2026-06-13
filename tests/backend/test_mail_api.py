"""Tests for the compatible mail fetch API endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.crypto import TokenCipher
from backend.app.models.enums import MailAccountOwnerType, MailAccountStatus, UserRole, UserStatus
from backend.app.models.mail_account import MailAccount
from backend.app.services.mail_accounts import resolve_or_create_mail_account
from backend.app.schemas.mail_accounts import MailAccountResolve
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
    user = await create_user(
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
        "backend.app.services.mail_fetchers.fetch_mail_for_account",
        new=AsyncMock(
            return_value=AsyncMock(
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
        "backend.app.services.mail_fetchers.fetch_mail_for_account",
        new=AsyncMock(
            return_value=AsyncMock(
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
    user = await create_user(
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
    from backend.app.core.config import get_settings

    cipher = TokenCipher(key=get_settings().token_encryption_key)
    await _create_account(test_session, "existing@outlook.com", "stored-rt", cipher)

    user = await create_user(
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
        "backend.app.services.mail_fetchers.fetch_mail_for_account",
        new=AsyncMock(
            return_value=AsyncMock(
                success=True, message_count=2, provider="graph"
            )
        ),
    ):
        # No client_id/refresh_token passed, but account already exists
        resp = await client.post(
            "/api/mail/fetch",
            json={"email": "existing@outlook.com"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
