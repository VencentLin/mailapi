"""Outlook mail fetching via Microsoft Graph API.

Phase 3A: Graph first, IMAP XOAUTH2 fallback.
"""

from __future__ import annotations

import asyncio
import base64
import imaplib
import logging
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser
from typing import Any

import httpx

from backend.app.models.mail_account import MailAccount

logger = logging.getLogger(__name__)

GRAPH_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MS_TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
GRAPH_MAIL_URL = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
IMAP_SCOPE = "https://outlook.office.com/IMAP.AccessAsUser.All offline_access"
HTTP_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# data types
# ---------------------------------------------------------------------------


@dataclass
class MailCredentials:
    email: str
    client_id: str
    refresh_token: str


@dataclass(frozen=True)
class OAuthToken:
    access_token: str
    refresh_token: str | None
    expires_in: int
    scope: str = ""

    @property
    def has_mail_read(self) -> bool:
        return "Mail.Read" in self.scope or "Mail.ReadWrite" in self.scope


@dataclass(frozen=True)
class MailItem:
    id: str
    sender: str
    subject: str
    text: str
    html: str | None
    received_at: str | None


@dataclass
class MailFetchResult:
    success: bool
    message_count: int = 0
    provider: str = "graph"
    raw_messages: list[dict[str, Any]] = field(default_factory=list)
    access_token_used: str = ""
    error_code: str | None = None
    error_detail: str | None = None


class MicrosoftOAuthError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message


class GraphMailPermissionError(Exception):
    """Graph token is valid but cannot read mail."""


class MailFetchError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: str = "mail_fetch_failed",
        protocol_attempts: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.protocol_attempts = protocol_attempts or []


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


class MicrosoftOAuthProvider:
    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._http_client = http_client

    async def refresh_graph_token(self, client_id: str, refresh_token: str) -> OAuthToken:
        return await self._refresh_token(
            client_id=client_id,
            refresh_token=refresh_token,
            scope=GRAPH_SCOPE,
        )

    async def refresh_imap_token(self, client_id: str, refresh_token: str) -> OAuthToken:
        return await self._refresh_token(
            client_id=client_id,
            refresh_token=refresh_token,
            scope=IMAP_SCOPE,
        )

    async def _refresh_token(
        self,
        *,
        client_id: str,
        refresh_token: str,
        scope: str,
    ) -> OAuthToken:
        payload = {
            "client_id": client_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": scope,
        }
        if self._http_client is not None:
            return await self._post_refresh(payload)
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http_client:
            self._http_client = http_client
            try:
                return await self._post_refresh(payload)
            finally:
                self._http_client = None

    async def _post_refresh(self, payload: dict[str, str]) -> OAuthToken:
        assert self._http_client is not None
        response = await self._http_client.post(MS_TOKEN_URL, data=payload)
        if response.status_code != 200:
            try:
                body = response.json()
            except ValueError:
                body = {}
            error_code = str(body.get("error") or f"oauth_{response.status_code}")
            message = str(body.get("error_description") or response.text[:500])
            raise MicrosoftOAuthError(response.status_code, error_code, message)
        body = response.json()
        return OAuthToken(
            access_token=str(body["access_token"]),
            refresh_token=body.get("refresh_token"),
            expires_in=int(body.get("expires_in", 0)),
            scope=str(body.get("scope", "")),
        )


# ---------------------------------------------------------------------------
# Graph API fetcher
# ---------------------------------------------------------------------------


def normalize_graph_mailbox(mailbox: str) -> str:
    if mailbox == "Junk":
        return "junkemail"
    return "inbox"


def _graph_message_to_item(message: dict[str, Any]) -> dict[str, Any]:
    sender = (
        message.get("from", {})
        .get("emailAddress", {})
        .get("address", "")
    )
    body = message.get("body") or {}
    return {
        "id": str(message.get("id", "")),
        "sender": str(sender),
        "subject": str(message.get("subject") or ""),
        "text": str(message.get("bodyPreview") or ""),
        "html": body.get("content"),
        "received_at": message.get("receivedDateTime") or message.get("createdDateTime"),
    }


class GraphMailFetcher:
    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._http_client = http_client

    async def list_messages(
        self,
        access_token: str,
        *,
        mailbox: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        folder = normalize_graph_mailbox(mailbox)
        url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder}/messages"
        params = {
            "$top": limit,
            "$orderby": "receivedDateTime desc",
            "$select": "id,from,subject,bodyPreview,body,receivedDateTime,createdDateTime",
        }
        response = await self._request(
            "GET",
            url,
            access_token=access_token,
            params=params,
        )
        data = response.json()
        return [_graph_message_to_item(item) for item in data.get("value", [])]

    async def clear_mailbox(self, access_token: str, *, mailbox: str) -> None:
        messages = await self.list_messages(access_token, mailbox=mailbox, limit=100)
        for message in messages:
            message_id = message["id"]
            await self._request(
                "DELETE",
                f"https://graph.microsoft.com/v1.0/me/messages/{message_id}",
                access_token=access_token,
            )

    async def _request(
        self,
        method: str,
        url: str,
        *,
        access_token: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {access_token}"}
        if self._http_client is not None:
            response = await self._http_client.request(
                method,
                url,
                headers=headers,
                params=params,
            )
        else:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http_client:
                response = await http_client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                )
        if response.status_code in {401, 403}:
            raise GraphMailPermissionError(response.text[:500])
        if response.status_code not in {200, 202, 204}:
            raise MailFetchError(
                response.text[:500],
                error_code=f"graph_{response.status_code}",
                protocol_attempts=["graph_failed"],
            )
        return response


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
# IMAP fallback
# ---------------------------------------------------------------------------


def generate_xoauth2_string(email: str, access_token: str) -> str:
    auth_string = f"user={email}\x01auth=Bearer {access_token}\x01\x01"
    return base64.b64encode(auth_string.encode("utf-8")).decode("ascii")


class ImapMailFetcher:
    host = "outlook.office365.com"
    port = 993

    async def list_messages(
        self,
        email: str,
        access_token: str,
        *,
        mailbox: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self._list_messages_sync,
            email,
            access_token,
            mailbox,
            limit,
        )

    async def clear_mailbox(self, email: str, access_token: str, *, mailbox: str) -> None:
        await asyncio.to_thread(self._clear_mailbox_sync, email, access_token, mailbox)

    def _connect(self, email: str, access_token: str) -> imaplib.IMAP4_SSL:
        connection = imaplib.IMAP4_SSL(self.host, self.port)
        xoauth2 = generate_xoauth2_string(email, access_token)
        connection.authenticate("XOAUTH2", lambda _: xoauth2.encode("ascii"))
        return connection

    def _list_messages_sync(
        self,
        email: str,
        access_token: str,
        mailbox: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        connection = self._connect(email, access_token)
        try:
            status, _ = connection.select(mailbox or "INBOX", readonly=True)
            if status != "OK":
                raise MailFetchError(
                    f"Unable to open IMAP mailbox {mailbox}",
                    error_code="imap_mailbox_open_failed",
                    protocol_attempts=["imap_failed"],
                )
            status, data = connection.search(None, "ALL")
            if status != "OK" or not data or not data[0]:
                return []
            message_ids = data[0].split()[-limit:]
            items: list[dict[str, Any]] = []
            for message_id in message_ids:
                fetch_status, message_data = connection.fetch(message_id, "(RFC822)")
                if fetch_status != "OK":
                    continue
                raw_message = next(
                    part[1]
                    for part in message_data
                    if isinstance(part, tuple) and isinstance(part[1], bytes)
                )
                items.append(self._parse_message(message_id.decode("ascii"), raw_message))
            return list(reversed(items))
        finally:
            connection.logout()

    def _clear_mailbox_sync(self, email: str, access_token: str, mailbox: str) -> None:
        connection = self._connect(email, access_token)
        try:
            status, _ = connection.select(mailbox or "INBOX", readonly=False)
            if status != "OK":
                raise MailFetchError(
                    f"Unable to open IMAP mailbox {mailbox}",
                    error_code="imap_mailbox_open_failed",
                    protocol_attempts=["imap_failed"],
                )
            status, data = connection.search(None, "ALL")
            if status == "OK" and data and data[0]:
                for message_id in data[0].split():
                    connection.store(message_id, "+FLAGS", "\\Deleted")
                connection.expunge()
        finally:
            connection.logout()

    def _parse_message(self, message_id: str, raw_message: bytes) -> dict[str, Any]:
        message = BytesParser(policy=policy.default).parsebytes(raw_message)
        text = ""
        html: str | None = None
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" and not text:
                    text = part.get_content()
                elif content_type == "text/html" and html is None:
                    html = part.get_content()
        else:
            content_type = message.get_content_type()
            if content_type == "text/html":
                html = message.get_content()
            else:
                text = message.get_content()
        return {
            "id": message_id,
            "sender": str(message.get("From") or ""),
            "subject": str(message.get("Subject") or ""),
            "text": text,
            "html": html,
            "received_at": str(message.get("Date") or ""),
        }


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


async def fetch_messages(
    credentials: MailCredentials,
    *,
    mailbox: str,
    limit: int,
    oauth_provider: MicrosoftOAuthProvider | Any | None = None,
    graph_fetcher: GraphMailFetcher | Any | None = None,
    imap_fetcher: ImapMailFetcher | Any | None = None,
) -> tuple[list[dict[str, Any]], str]:
    oauth = oauth_provider or MicrosoftOAuthProvider()
    graph = graph_fetcher or GraphMailFetcher()
    imap = imap_fetcher or ImapMailFetcher()
    attempts: list[str] = []

    try:
        graph_token = await oauth.refresh_graph_token(
            credentials.client_id,
            credentials.refresh_token,
        )
        if graph_token.has_mail_read:
            try:
                items = await graph.list_messages(
                    graph_token.access_token,
                    mailbox=mailbox,
                    limit=limit,
                )
                return items, "graph"
            except GraphMailPermissionError:
                attempts.append("graph_permission_failed")
        else:
            attempts.append("graph_no_mail_read")
    except Exception as exc:
        attempts.append("graph_failed")
        logger.warning("Graph fetch path failed: %s", exc)

    try:
        imap_token = await oauth.refresh_imap_token(
            credentials.client_id,
            credentials.refresh_token,
        )
        items = await imap.list_messages(
            credentials.email,
            imap_token.access_token,
            mailbox=mailbox,
            limit=limit,
        )
        return items, "imap"
    except Exception as exc:
        attempts.append("imap_failed")
        raise MailFetchError(
            str(exc),
            error_code="mail_fetch_failed",
            protocol_attempts=attempts,
        ) from exc


async def clear_mailbox(
    credentials: MailCredentials,
    *,
    mailbox: str,
    oauth_provider: MicrosoftOAuthProvider | Any | None = None,
    graph_fetcher: GraphMailFetcher | Any | None = None,
    imap_fetcher: ImapMailFetcher | Any | None = None,
) -> str:
    oauth = oauth_provider or MicrosoftOAuthProvider()
    graph = graph_fetcher or GraphMailFetcher()
    imap = imap_fetcher or ImapMailFetcher()
    graph_token = await oauth.refresh_graph_token(
        credentials.client_id,
        credentials.refresh_token,
    )
    if graph_token.has_mail_read:
        try:
            await graph.clear_mailbox(graph_token.access_token, mailbox=mailbox)
            return "graph"
        except GraphMailPermissionError:
            pass
    imap_token = await oauth.refresh_imap_token(
        credentials.client_id,
        credentials.refresh_token,
    )
    await imap.clear_mailbox(
        credentials.email,
        imap_token.access_token,
        mailbox=mailbox,
    )
    return "imap"


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
        credentials = MailCredentials(
            email=self._account.email,
            client_id=self._account.client_id,
            refresh_token=self._decrypted_token,
        )
        try:
            items, protocol = await fetch_messages(
                credentials,
                mailbox="INBOX",
                limit=top,
            )
        except MailFetchError as exc:
            return MailFetchResult(
                success=False,
                error_code=exc.error_code,
                error_detail=str(exc),
            )
        return MailFetchResult(
            success=True,
            message_count=len(items),
            provider=protocol,
            raw_messages=items,
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
