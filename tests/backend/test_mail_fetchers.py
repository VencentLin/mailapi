"""Tests for Outlook mail fetcher (Graph API + IMAP)."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, patch

import pytest
from httpx import Response

from backend.app.models.enums import MailAccountOwnerType, MailAccountStatus
from backend.app.models.mail_account import MailAccount
from backend.app.services.mail_fetchers import (
    GraphMailPermissionError,
    MailCredentials,
    MailFetcher,
    MailFetchError,
    create_fetcher,
    fetch_mail_for_account,
    fetch_messages,
    generate_xoauth2_string,
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


def test_generate_xoauth2_string_matches_microsoft_format():
    encoded = generate_xoauth2_string("user@example.com", "access-token")

    decoded = base64.b64decode(encoded).decode()

    assert decoded == "user=user@example.com\x01auth=Bearer access-token\x01\x01"


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
        "backend.app.services.mail_fetchers.fetch_messages",
        new=AsyncMock(return_value=([{"id": "m1"}, {"id": "m2"}], "graph")),
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
        "backend.app.services.mail_fetchers.fetch_messages",
        new=AsyncMock(
            side_effect=MailFetchError(
                "Could not obtain access token from refresh token",
                error_code="TOKEN_REFRESH_FAILED",
            )
        ),
    ):
        result = await fetch_mail_for_account(account, decrypted_token="rt")

    assert result.success is False
    assert result.error_code == "TOKEN_REFRESH_FAILED"


@pytest.mark.asyncio
async def test_fetch_messages_uses_imap_when_graph_token_lacks_mail_read():
    credentials = MailCredentials(
        email="test@outlook.com",
        client_id="client-id",
        refresh_token="refresh-token",
    )
    graph_token = AsyncMock(
        access_token="graph-token",
        refresh_token=None,
        expires_in=3600,
        scope="User.Read",
        has_mail_read=False,
    )
    imap_token = AsyncMock(
        access_token="imap-token",
        refresh_token=None,
        expires_in=3600,
        scope="https://outlook.office.com/IMAP.AccessAsUser.All",
        has_mail_read=False,
    )
    oauth_provider = AsyncMock()
    oauth_provider.refresh_graph_token.return_value = graph_token
    oauth_provider.refresh_imap_token.return_value = imap_token
    graph_fetcher = AsyncMock()
    imap_fetcher = AsyncMock()
    imap_fetcher.list_messages.return_value = [
        {
            "id": "imap-1",
            "sender": "sender@example.com",
            "subject": "Code",
            "text": "123456",
            "html": None,
            "received_at": "2026-06-13T01:00:00Z",
        }
    ]

    items, protocol = await fetch_messages(
        credentials,
        mailbox="INBOX",
        limit=1,
        oauth_provider=oauth_provider,
        graph_fetcher=graph_fetcher,
        imap_fetcher=imap_fetcher,
    )

    assert protocol == "imap"
    assert items[0]["id"] == "imap-1"
    graph_fetcher.list_messages.assert_not_called()
    imap_fetcher.list_messages.assert_awaited_once_with(
        "test@outlook.com",
        "imap-token",
        mailbox="INBOX",
        limit=1,
    )


@pytest.mark.asyncio
async def test_fetch_messages_falls_back_to_imap_when_graph_is_unauthorized():
    credentials = MailCredentials(
        email="test@outlook.com",
        client_id="client-id",
        refresh_token="refresh-token",
    )
    graph_token = AsyncMock(
        access_token="graph-token",
        refresh_token=None,
        expires_in=3600,
        scope="https://graph.microsoft.com/Mail.Read",
        has_mail_read=True,
    )
    imap_token = AsyncMock(
        access_token="imap-token",
        refresh_token=None,
        expires_in=3600,
        scope="https://outlook.office.com/IMAP.AccessAsUser.All",
        has_mail_read=False,
    )
    oauth_provider = AsyncMock()
    oauth_provider.refresh_graph_token.return_value = graph_token
    oauth_provider.refresh_imap_token.return_value = imap_token
    graph_fetcher = AsyncMock()
    graph_fetcher.list_messages.side_effect = GraphMailPermissionError(
        "Graph token cannot read mail"
    )
    imap_fetcher = AsyncMock()
    imap_fetcher.list_messages.return_value = []

    items, protocol = await fetch_messages(
        credentials,
        mailbox="INBOX",
        limit=1,
        oauth_provider=oauth_provider,
        graph_fetcher=graph_fetcher,
        imap_fetcher=imap_fetcher,
    )

    assert items == []
    assert protocol == "imap"
    graph_fetcher.list_messages.assert_awaited_once_with(
        "graph-token",
        mailbox="INBOX",
        limit=1,
    )
    imap_fetcher.list_messages.assert_awaited_once_with(
        "test@outlook.com",
        "imap-token",
        mailbox="INBOX",
        limit=1,
    )


@pytest.mark.asyncio
async def test_fetch_messages_raises_structured_error_when_graph_and_imap_fail():
    credentials = MailCredentials(
        email="test@outlook.com",
        client_id="client-id",
        refresh_token="refresh-token",
    )
    graph_token = AsyncMock(
        access_token="graph-token",
        refresh_token=None,
        expires_in=3600,
        scope="User.Read",
        has_mail_read=False,
    )
    oauth_provider = AsyncMock()
    oauth_provider.refresh_graph_token.return_value = graph_token
    oauth_provider.refresh_imap_token.side_effect = RuntimeError("imap token failed")

    with pytest.raises(MailFetchError) as exc:
        await fetch_messages(
            credentials,
            mailbox="INBOX",
            limit=1,
            oauth_provider=oauth_provider,
            graph_fetcher=AsyncMock(),
            imap_fetcher=AsyncMock(),
        )

    assert exc.value.error_code == "mail_fetch_failed"
    assert exc.value.protocol_attempts == ["graph_no_mail_read", "imap_failed"]
