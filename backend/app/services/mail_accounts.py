"""Mail account ownership resolution service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.crypto import TokenCipher
from backend.app.models.enums import MailAccountOwnerType, MailAccountStatus
from backend.app.models.mail_account import MailAccount
from backend.app.models.user import User
from backend.app.schemas.mail_accounts import MailAccountResolve, MailAccountResolved


class MailAccountNotReadyError(Exception):
    """Raised when a new mail account lacks required credentials."""


def _cipher() -> TokenCipher:
    return TokenCipher(key=get_settings().token_encryption_key)


async def _get_by_email(session: AsyncSession, email: str) -> MailAccount | None:
    normalized = email.strip().lower()
    result = await session.execute(
        select(MailAccount).where(MailAccount.email == normalized)
    )
    return result.scalar_one_or_none()


async def resolve_or_create_mail_account(
    session: AsyncSession,
    *,
    user: User | None,
    resolve: MailAccountResolve,
) -> MailAccountResolved:
    """Find or create a mail account for the given email.

    - Existing account → return it (ignoring new credentials).
    - New account + user → create user-owned.
    - New account + no user → create public.
    - New account with missing client_id or refresh_token → raise.
    """
    email = resolve.email.strip().lower()
    existing = await _get_by_email(session, email)

    if existing is not None:
        return MailAccountResolved(account=existing, created=False)

    # New account — validate required fields
    if not resolve.client_id:
        raise MailAccountNotReadyError("client_id is required for new mail accounts")
    if not resolve.refresh_token:
        raise MailAccountNotReadyError("refresh_token is required for new mail accounts")

    owner_type = MailAccountOwnerType.USER if user is not None else MailAccountOwnerType.PUBLIC

    account = MailAccount(
        email=email,
        client_id=resolve.client_id,
        refresh_token_encrypted=_cipher().encrypt(resolve.refresh_token),
        owner_type=owner_type,
        owner_user_id=user.id if user is not None else None,
        status=MailAccountStatus.ACTIVE,
        created_via="api",
        created_by_user_id=user.id if user is not None else None,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    return MailAccountResolved(account=account, created=True)
