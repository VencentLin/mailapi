from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.crypto import TokenCipher
from backend.app.db.session import get_db_session
from backend.app.models.enums import MailAccountOwnerType, MailAccountStatus, UserRole, UserStatus
from backend.app.models.mail_account import MailAccount
from backend.app.models.user import User
from backend.app.services.audit_logs import write_audit_log
from backend.app.services.microsoft_oauth import (
    MicrosoftOAuthClient,
    MicrosoftOAuthConfigError,
    MicrosoftOAuthError,
    decode_reauthorize_state,
)

router = APIRouter(prefix="/oauth/microsoft", tags=["oauth"])


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def _can_manage_account(user: User, account: MailAccount) -> bool:
    if _is_admin(user):
        return True
    return account.owner_type == MailAccountOwnerType.USER and account.owner_user_id == user.id


def _redirect_url(
    status: str,
    *,
    email: str | None = None,
    reason: str | None = None,
) -> str:
    params = {"reauthorize": status}
    if email:
        params["email"] = email
    if reason:
        params["reason"] = reason
    return f"/mail-accounts?{urlencode(params)}"


def _redirect_failed(reason: str) -> RedirectResponse:
    return RedirectResponse(_redirect_url("failed", reason=reason), status_code=302)


@router.get("/callback")
async def microsoft_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    if error:
        return _redirect_failed("microsoft_denied")
    if not code or not state:
        return _redirect_failed("missing_code")

    try:
        decoded_state = decode_reauthorize_state(state)
    except ValueError:
        return _redirect_failed("invalid_state")

    user = await session.get(User, decoded_state.user_id)
    account = await session.get(MailAccount, decoded_state.account_id)
    if user is None or user.status != UserStatus.ACTIVE or account is None:
        return _redirect_failed("not_found")
    if not _can_manage_account(user, account):
        return _redirect_failed("permission_denied")

    oauth_client = MicrosoftOAuthClient()
    try:
        token_result = await oauth_client.exchange_code(code)
        profile_email = await oauth_client.fetch_profile_email(token_result.access_token)
    except (MicrosoftOAuthConfigError, MicrosoftOAuthError):
        return _redirect_failed("oauth_failed")

    if profile_email != account.email.strip().lower():
        return _redirect_failed("email_mismatch")

    settings = get_settings()
    cipher = TokenCipher(key=settings.token_encryption_key)
    account.client_id = settings.microsoft_oauth_client_id or account.client_id
    account.refresh_token_encrypted = cipher.encrypt(token_result.refresh_token)
    account.status = MailAccountStatus.ACTIVE
    account.last_error_code = None

    await write_audit_log(
        session,
        actor_user_id=user.id,
        action="mail_account.credentials.reauthorize",
        target_type="mail_account",
        target_id=str(account.id),
        metadata={"email": account.email},
        ip_address=request.client.host if request.client else None,
    )
    return RedirectResponse(
        _redirect_url("success", email=account.email),
        status_code=302,
    )
