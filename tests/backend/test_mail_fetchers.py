"""Tests for Outlook mail fetcher (Graph API + IMAP)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import Response

from backend.app.models.enums import MailAccountOwnerType, MailAccountStatus
from backend.app.models.mail_account import MailAccount
from backend.app.services.mail_fetchers import (
    MailFetcher,
    MailFetchResult,
    create_fetcher,
    fetch_mail_for_account,
    is_oauth_error,
)


# ---------------------------------------------------------------------------
# create_fetcher
# ---------------------------------------------------------------------------


def test_create_fetcher_returns_graph_fetcher_for_outlook():
    account = MailAccount(
        email="test@outlook.com",
        client_id="cid",
        refresh_token_encrypted="encrypted-rt",
        owner_type=MailAccountOwnerType.USER,
        status=MailAccountStatus.ACTIVE,
        created_via="api",
    )
    fetcher = create_fetcher(account, decrypted_token="rt-plain")
    assert isinstance(fetcher, MailFetcher)
    assert fetcher._account is account  # noqa: SLF001
    assert fetcher._decrypted_token == "rt-plain"  # noqa: SLF001


# ---------------------------------------------------------------------------
# is_oauth_error
# ---------------------------------------------------------------------------


def test_is_oauth_error_detects_401_with_insufficient_claims():
    resp = Response(401, json={"error": "invalid_grant"})
    assert is_oauth_error(resp) is True


def test_is_oauth_error_detects_401_with_expired_token():
    resp = Response(401, json={"error": "expired_token"})
    assert is_oauth_error(resp) is True


def test_is_oauth_error_returns_false_for_403():
    resp = Response(403, json={})
    assert is_oauth_error(resp) is False


def test_is_oauth_error_returns_false_for_500():
    resp = Response(500, json={})
    assert is_oauth_error(resp) is False


# ---------------------------------------------------------------------------
# fetch_mail_for_account (unit test — mocks token refresh + Graph)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_mail_for_account_refreshes_token_then_fetches():
    account = MailAccount(
        email="test@outlook.com",
        client_id="cid",
        refresh_token_encrypted="encrypted-rt",
        owner_type=MailAccountOwnerType.USER,
        status=MailAccountStatus.ACTIVE,
        created_via="api",
    )

    with patch(
        "backend.app.services.mail_fetchers._refresh_access_token",
        new=AsyncMock(return_value="new-access-token"),
    ), patch(
        "backend.app.services.mail_fetchers._fetch_graph_messages",
        new=AsyncMock(
            return_value=MailFetchResult(
                success=True,
                message_count=2,
                provider="graph",
                raw_messages=[],
                access_token_used="new-access-token",
            )
        ),
    ):
        result = await fetch_mail_for_account(account, decrypted_token="rt")

    assert result.success is True
    assert result.message_count == 2
    assert result.provider == "graph"


@pytest.mark.asyncio
async def test_fetch_mail_for_account_handles_token_refresh_failure():
    account = MailAccount(
        email="test@outlook.com",
        client_id="cid",
        refresh_token_encrypted="encrypted-rt",
        owner_type=MailAccountOwnerType.USER,
        status=MailAccountStatus.ACTIVE,
        created_via="api",
    )

    with patch(
        "backend.app.services.mail_fetchers._refresh_access_token",
        new=AsyncMock(return_value=None),
    ):
        result = await fetch_mail_for_account(account, decrypted_token="rt")

    assert result.success is False
    assert result.error_code == "TOKEN_REFRESH_FAILED"
