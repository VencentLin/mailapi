"""Compatible mail fetch API.

POST /api/mail/fetch
  - Authenticated: user-owned account
  - Anonymous: public account
  - Existing account: uses stored credentials
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.crypto import TokenCipher
from backend.app.core.security import decode_access_token
from backend.app.db.session import get_db_session
from backend.app.models.enums import UserStatus
from backend.app.models.user import User
from backend.app.schemas.mail_accounts import MailAccountResolve
from backend.app.services.mail_accounts import (
    MailAccountNotReadyError,
    resolve_or_create_mail_account,
)
from backend.app.services.mail_fetchers import fetch_mail_for_account
from backend.app.services.users import get_user_by_id

router = APIRouter(prefix="/mail", tags=["mail"])

bearer_scheme = HTTPBearer(auto_error=False)


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User | None:
    """Return the authenticated user, or None if no valid token is present."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        return None
    subject = payload.get("sub")
    if not subject:
        return None
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        return None
    user = await get_user_by_id(session, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        return None
    return user


@router.post("/fetch")
async def fetch_mail(
    resolve: MailAccountResolve,
    session: AsyncSession = Depends(get_db_session),
    user: User | None = Depends(get_optional_user),
) -> dict:
    """Fetch mail for the given email address.

    - First call with valid credentials → account is created (user-owned or public).
    - Subsequent calls → stored credentials are used (new credentials ignored).
    - Missing client_id/refresh_token for a new account → 400 error.
    """
    try:
        result = await resolve_or_create_mail_account(
            session, user=user, resolve=resolve
        )
    except MailAccountNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    cipher = TokenCipher(key=get_settings().token_encryption_key)
    decrypted_token = cipher.decrypt(result.account.refresh_token_encrypted)

    fetch_result = await fetch_mail_for_account(
        result.account,
        decrypted_token=decrypted_token,
    )
    return asdict(fetch_result)
