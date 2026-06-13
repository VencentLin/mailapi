"""Outlook mail fetching via Microsoft Graph API.

Phase 3A: Graph API only. IMAP support is deferred to Phase 3B.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from backend.app.models.mail_account import MailAccount

logger = logging.getLogger(__name__)

GRAPH_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH_MAIL_URL = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
HTTP_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# data types
# ---------------------------------------------------------------------------


@dataclass
class MailFetchResult:
    success: bool
    message_count: int = 0
    provider: str = "graph"
    raw_messages: list[dict[str, Any]] = field(default_factory=list)
    access_token_used: str = ""
    error_code: str | None = None
    error_detail: str | None = None


# ---------------------------------------------------------------------------
# OAuth helpers
# ---------------------------------------------------------------------------


def is_oauth_error(response: httpx.Response) -> bool:
    """Return True if the response indicates an OAuth token issue."""
    if response.status_code != 401:
        return False
    try:
        body = response.json()
    except Exception:
        return True
    error = body.get("error", "")
    return isinstance(error, str) and (
        "invalid_grant" in error or "expired" in error or "unauthorized" in error.lower()
    )


async def _refresh_access_token(client_id: str, refresh_token: str) -> str | None:
    """Exchange a refresh token for a new access token via Microsoft OAuth."""
    payload = {
        "client_id": client_id,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": GRAPH_SCOPE,
    }
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            resp = await http.post(GRAPH_TOKEN_URL, data=payload)
            if resp.status_code != 200:
                logger.warning("Token refresh failed: %s %s", resp.status_code, resp.text[:200])
                return None
            data = resp.json()
            return data.get("access_token")
    except httpx.RequestError as exc:
        logger.warning("Token refresh network error: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Graph API fetcher
# ---------------------------------------------------------------------------


async def _fetch_graph_messages(
    access_token: str,
    *,
    top: int = 10,
    target_email: str = "",
) -> MailFetchResult:
    """Fetch the latest *top* messages from the user's inbox via Graph API."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    params: dict[str, Any] = {
        "$top": top,
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,toRecipients,body,receivedDateTime,hasAttachments",
    }
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            resp = await http.get(GRAPH_MAIL_URL, headers=headers, params=params)
            if resp.status_code == 401:
                return MailFetchResult(
                    success=False,
                    error_code="OAUTH_ERROR",
                    error_detail="Access token rejected by Graph",
                )
            if resp.status_code != 200:
                return MailFetchResult(
                    success=False,
                    error_code=f"GRAPH_{resp.status_code}",
                    error_detail=resp.text[:500],
                )
            data = resp.json()
            messages = data.get("value", [])
            return MailFetchResult(
                success=True,
                message_count=len(messages),
                provider="graph",
                raw_messages=messages,
                access_token_used=access_token,
            )
    except httpx.RequestError as exc:
        return MailFetchResult(
            success=False,
            error_code="NETWORK_ERROR",
            error_detail=str(exc),
        )


# ---------------------------------------------------------------------------
# fetcher interface
# ---------------------------------------------------------------------------


class MailFetcher:
    """Knows how to fetch mail for one account.

    The decrypted refresh token is passed in (not stored) so the caller
    controls the encryption lifecycle.
    """

    def __init__(self, account: MailAccount, *, decrypted_token: str) -> None:
        self._account = account
        self._decrypted_token = decrypted_token

    async def fetch(self, *, top: int = 10) -> MailFetchResult:
        """Refresh token → fetch inbox messages."""
        access_token = await _refresh_access_token(
            self._account.client_id, self._decrypted_token
        )
        if access_token is None:
            return MailFetchResult(
                success=False,
                error_code="TOKEN_REFRESH_FAILED",
                error_detail="Could not obtain access token from refresh token",
            )
        return await _fetch_graph_messages(
            access_token, top=top, target_email=self._account.email
        )


# ---------------------------------------------------------------------------
# public entry point
# ---------------------------------------------------------------------------


def create_fetcher(account: MailAccount, *, decrypted_token: str) -> MailFetcher:
    """Create a fetcher for the given mail account."""
    return MailFetcher(account, decrypted_token=decrypted_token)


async def fetch_mail_for_account(
    account: MailAccount,
    *,
    decrypted_token: str,
    top: int = 10,
) -> MailFetchResult:
    """Convenience function: fetch mail for a single account."""
    fetcher = create_fetcher(account, decrypted_token=decrypted_token)
    return await fetcher.fetch(top=top)
