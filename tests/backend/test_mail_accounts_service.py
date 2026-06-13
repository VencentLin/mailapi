"""Tests for mail account ownership resolution service."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.crypto import TokenCipher
from backend.app.models.enums import MailAccountOwnerType, MailAccountStatus, UserRole
from backend.app.schemas.mail_accounts import MailAccountResolve
from backend.app.services.mail_accounts import (
    MailAccountNotReadyError,
    resolve_or_create_mail_account,
)
from backend.app.services.users import create_user

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _cipher() -> TokenCipher:
    return TokenCipher(key=get_settings().token_encryption_key)


# ---------------------------------------------------------------------------
# resolve_or_create_mail_account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_call_with_user_creates_user_owned_account(test_session: AsyncSession):
    """Authenticated user, email doesn't exist → create user-owned account."""
    user = await create_user(
        test_session,
        username="u1",
        email="u1@example.com",
        password="pw",
        role=UserRole.USER,
    )

    result = await resolve_or_create_mail_account(
        test_session,
        user=user,
        resolve=MailAccountResolve(
            email="u1@outlook.com",
            client_id="cid-1",
            refresh_token="rt-secret-1",
        ),
    )

    assert result.account.email == "u1@outlook.com"
    assert result.account.owner_type == MailAccountOwnerType.USER
    assert result.account.owner_user_id == user.id
    assert result.account.status == MailAccountStatus.ACTIVE
    assert result.account.created_via == "api"
    assert result.created is True

    # Verify refresh token is encrypted in DB, not plaintext
    row = (
        await test_session.execute(
            text("SELECT refresh_token_encrypted FROM mail_accounts WHERE email = 'u1@outlook.com'")
        )
    )
    db_token = row.scalar_one()
    assert "rt-secret-1" not in db_token
    assert _cipher().decrypt(db_token) == "rt-secret-1"


@pytest.mark.asyncio
async def test_first_call_without_user_creates_public_account(test_session: AsyncSession):
    """No user, email doesn't exist → create public account."""
    result = await resolve_or_create_mail_account(
        test_session,
        user=None,
        resolve=MailAccountResolve(
            email="public@outlook.com",
            client_id="cid-pub",
            refresh_token="rt-pub",
        ),
    )

    assert result.account.owner_type == MailAccountOwnerType.PUBLIC
    assert result.account.owner_user_id is None
    assert result.created is True


@pytest.mark.asyncio
async def test_existing_account_uses_stored_credentials(test_session: AsyncSession):
    """Email already exists → return existing, ignore new credentials."""
    # Create via first call
    await resolve_or_create_mail_account(
        test_session,
        user=None,
        resolve=MailAccountResolve(
            email="existing@outlook.com",
            client_id="old-cid",
            refresh_token="old-rt",
        ),
    )

    # Second call with different credentials
    result = await resolve_or_create_mail_account(
        test_session,
        user=None,
        resolve=MailAccountResolve(
            email="existing@outlook.com",
            client_id="new-cid",
            refresh_token="new-rt",
        ),
    )

    assert result.created is False
    # Stored refresh token should still be the old one
    assert _cipher().decrypt(result.account.refresh_token_encrypted) == "old-rt"


@pytest.mark.asyncio
async def test_email_normalization_strip_and_lower(test_session: AsyncSession):
    """Email is normalized: stripped and lowercased."""
    result = await resolve_or_create_mail_account(
        test_session,
        user=None,
        resolve=MailAccountResolve(
            email="  MixedCase@Outlook.COM  ",
            client_id="cid",
            refresh_token="rt",
        ),
    )

    assert result.account.email == "mixedcase@outlook.com"


@pytest.mark.asyncio
async def test_normalized_duplicate_is_detected(test_session: AsyncSession):
    """Same email with different casing → treated as duplicate."""
    await resolve_or_create_mail_account(
        test_session,
        user=None,
        resolve=MailAccountResolve(
            email="dup@outlook.com",
            client_id="cid",
            refresh_token="rt",
        ),
    )

    result = await resolve_or_create_mail_account(
        test_session,
        user=None,
        resolve=MailAccountResolve(
            email="  DUP@OUTLOOK.COM  ",
            client_id="cid-other",
            refresh_token="rt-other",
        ),
    )

    assert result.created is False
    assert result.account.email == "dup@outlook.com"


@pytest.mark.asyncio
async def test_missing_client_id_raises_error(test_session: AsyncSession):
    """New email without client_id → MailAccountNotReadyError."""
    with pytest.raises(MailAccountNotReadyError, match="client_id"):
        await resolve_or_create_mail_account(
            test_session,
            user=None,
            resolve=MailAccountResolve(
                email="new@outlook.com",
                client_id="",
                refresh_token="rt",
            ),
        )


@pytest.mark.asyncio
async def test_missing_refresh_token_raises_error(test_session: AsyncSession):
    """New email without refresh_token → MailAccountNotReadyError."""
    with pytest.raises(MailAccountNotReadyError, match="refresh_token"):
        await resolve_or_create_mail_account(
            test_session,
            user=None,
            resolve=MailAccountResolve(
                email="new2@outlook.com",
                client_id="cid",
                refresh_token="",
            ),
        )


@pytest.mark.asyncio
async def test_existing_disabled_account_still_returned(test_session: AsyncSession):
    """Even a disabled account is returned (caller decides what to do)."""
    # Create account then manually disable it
    result = await resolve_or_create_mail_account(
        test_session,
        user=None,
        resolve=MailAccountResolve(
            email="disabled@outlook.com",
            client_id="cid",
            refresh_token="rt",
        ),
    )
    result.account.status = MailAccountStatus.DISABLED
    await test_session.commit()

    # Second call returns existing (disabled) account
    result2 = await resolve_or_create_mail_account(
        test_session,
        user=None,
        resolve=MailAccountResolve(
            email="disabled@outlook.com",
            client_id="cid2",
            refresh_token="rt2",
        ),
    )
    assert result2.created is False
    assert result2.account.status == MailAccountStatus.DISABLED
