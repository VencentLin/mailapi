from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt

from backend.app.core.config import get_settings
from backend.app.core.security import ALGORITHM

AUTHORIZE_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"
REAUTHORIZE_STATE_PURPOSE = "mail_account_reauthorize"
REAUTHORIZE_STATE_EXPIRES_SECONDS = 600


class MicrosoftOAuthConfigError(RuntimeError):
    """Raised when Microsoft OAuth settings are missing."""


class MicrosoftOAuthError(RuntimeError):
    """Raised when Microsoft OAuth exchange or profile lookup fails."""


@dataclass(frozen=True)
class ReauthorizeState:
    account_id: int
    user_id: int


@dataclass(frozen=True)
class ReauthorizeUrl:
    auth_url: str
    expires_in: int


@dataclass(frozen=True)
class OAuthTokenResult:
    access_token: str
    refresh_token: str


def _require_oauth_setting(value: str | None, name: str) -> str:
    if not value:
        raise MicrosoftOAuthConfigError(f"{name} is not configured")
    return value


def _tenant() -> str:
    tenant = (get_settings().microsoft_oauth_tenant or "consumers").strip()
    return tenant or "consumers"


def create_reauthorize_state(*, account_id: int, user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "purpose": REAUTHORIZE_STATE_PURPOSE,
        "account_id": account_id,
        "user_id": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=REAUTHORIZE_STATE_EXPIRES_SECONDS),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_reauthorize_state(state: str) -> ReauthorizeState:
    settings = get_settings()
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid OAuth state") from exc
    if payload.get("purpose") != REAUTHORIZE_STATE_PURPOSE:
        raise ValueError("Invalid OAuth state purpose")
    try:
        return ReauthorizeState(
            account_id=int(payload["account_id"]),
            user_id=int(payload["user_id"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid OAuth state payload") from exc


def build_reauthorize_url(*, account_id: int, user_id: int, login_hint: str) -> ReauthorizeUrl:
    settings = get_settings()
    client_id = _require_oauth_setting(
        settings.microsoft_oauth_client_id,
        "MICROSOFT_OAUTH_CLIENT_ID",
    )
    redirect_uri = _require_oauth_setting(
        settings.microsoft_oauth_redirect_uri,
        "MICROSOFT_OAUTH_REDIRECT_URI",
    )
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": settings.microsoft_oauth_scopes,
        "state": create_reauthorize_state(account_id=account_id, user_id=user_id),
        "login_hint": login_hint,
    }
    if settings.microsoft_oauth_prompt:
        params["prompt"] = settings.microsoft_oauth_prompt
    auth_url = f"{AUTHORIZE_URL_TEMPLATE.format(tenant=_tenant())}?{urlencode(params)}"
    return ReauthorizeUrl(auth_url=auth_url, expires_in=REAUTHORIZE_STATE_EXPIRES_SECONDS)


class MicrosoftOAuthClient:
    async def exchange_code(self, code: str) -> OAuthTokenResult:
        settings = get_settings()
        client_id = _require_oauth_setting(
            settings.microsoft_oauth_client_id,
            "MICROSOFT_OAUTH_CLIENT_ID",
        )
        redirect_uri = _require_oauth_setting(
            settings.microsoft_oauth_redirect_uri,
            "MICROSOFT_OAUTH_REDIRECT_URI",
        )
        data = {
            "client_id": client_id,
            "scope": settings.microsoft_oauth_scopes,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        if settings.microsoft_oauth_client_secret:
            data["client_secret"] = settings.microsoft_oauth_client_secret

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                TOKEN_URL_TEMPLATE.format(tenant=_tenant()),
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if response.status_code != 200:
            raise MicrosoftOAuthError("token_exchange_failed")

        body = response.json()
        access_token = str(body.get("access_token") or "")
        refresh_token = str(body.get("refresh_token") or "")
        if not access_token or not refresh_token:
            raise MicrosoftOAuthError("token_response_missing_tokens")
        return OAuthTokenResult(access_token=access_token, refresh_token=refresh_token)

    async def fetch_profile_email(self, access_token: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                GRAPH_ME_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if response.status_code != 200:
            raise MicrosoftOAuthError("profile_lookup_failed")

        body: dict[str, Any] = response.json()
        candidates: list[Any] = [
            body.get("mail"),
            body.get("userPrincipalName"),
        ]
        other_mails = body.get("otherMails")
        if isinstance(other_mails, list):
            candidates.extend(other_mails)
        for candidate in candidates:
            email = str(candidate or "").strip().lower()
            if email:
                return email
        raise MicrosoftOAuthError("profile_email_missing")
