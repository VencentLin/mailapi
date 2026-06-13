from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.routes.auth import get_current_user
from backend.app.core.config import get_settings
from backend.app.core.crypto import TokenCipher
from backend.app.db.session import get_db_session
from backend.app.models.enums import MailAccountOwnerType, MailAccountStatus, UserRole
from backend.app.models.logs import MailAccountClaim
from backend.app.models.mail_account import MailAccount
from backend.app.models.user import User
from backend.app.schemas.mail_accounts import (
    MailAccountCreate,
    MailAccountCredentialsPublic,
    MailAccountCredentialsUpdate,
    MailAccountPublic,
    MailAccountTestFetchResponse,
    MailAccountUpdate,
)
from backend.app.services.audit_logs import write_audit_log
from backend.app.services.mail_fetch_logs import write_mail_fetch_log
from backend.app.services.mail_fetchers import MailCredentials, clear_mailbox, fetch_messages

router = APIRouter(prefix="/mail-accounts", tags=["mail-accounts"])


def _cipher() -> TokenCipher:
    return TokenCipher(key=get_settings().token_encryption_key)


def _duration_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def _can_access_account(user: User, account: MailAccount) -> bool:
    if _is_admin(user):
        return True
    return account.owner_type == MailAccountOwnerType.PUBLIC or account.owner_user_id == user.id


def _can_manage_account(user: User, account: MailAccount) -> bool:
    if _is_admin(user):
        return True
    return account.owner_type == MailAccountOwnerType.USER and account.owner_user_id == user.id


def _public_account(account: MailAccount, current_user: User) -> MailAccountPublic:
    return MailAccountPublic(
        id=account.id,
        email=account.email,
        client_id=account.client_id,
        owner_type=account.owner_type,
        owner_user_id=account.owner_user_id,
        status=account.status,
        default_proxy=account.default_proxy,
        last_protocol=account.last_protocol,
        last_success_at=account.last_success_at,
        last_error_code=account.last_error_code,
        remark=account.remark,
        created_by_user_id=account.created_by_user_id,
        created_via=account.created_via,
        created_at=account.created_at,
        updated_at=account.updated_at,
        can_claim=account.owner_type == MailAccountOwnerType.PUBLIC,
        can_view_credentials=_is_admin(current_user),
    )


async def _get_account_or_404(session: AsyncSession, account_id: int) -> MailAccount:
    account = await session.get(MailAccount, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mail account not found")
    return account


async def _get_visible_account(
    session: AsyncSession,
    account_id: int,
    current_user: User,
) -> MailAccount:
    account = await _get_account_or_404(session, account_id)
    if not _can_access_account(current_user, account):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return account


async def _get_manageable_account(
    session: AsyncSession,
    account_id: int,
    current_user: User,
) -> MailAccount:
    account = await _get_account_or_404(session, account_id)
    if not _can_manage_account(current_user, account):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return account


def _credentials(account: MailAccount) -> MailCredentials:
    return MailCredentials(
        email=account.email,
        client_id=account.client_id,
        refresh_token=_cipher().decrypt(account.refresh_token_encrypted),
    )


@router.get("", response_model=list[MailAccountPublic])
async def list_mail_accounts(
    owner_user_id: int | None = Query(default=None),
    owner_type: MailAccountOwnerType | None = Query(default=None),
    email: str | None = Query(default=None),
    status_filter: MailAccountStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[MailAccountPublic]:
    stmt = select(MailAccount)
    if not _is_admin(current_user):
        stmt = stmt.where(
            or_(
                MailAccount.owner_type == MailAccountOwnerType.PUBLIC,
                MailAccount.owner_user_id == current_user.id,
            )
        )
    if owner_user_id is not None:
        stmt = stmt.where(MailAccount.owner_user_id == owner_user_id)
    if owner_type is not None:
        stmt = stmt.where(MailAccount.owner_type == owner_type)
    if email:
        stmt = stmt.where(MailAccount.email.ilike(f"%{email.strip().lower()}%"))
    if status_filter is not None:
        stmt = stmt.where(MailAccount.status == status_filter)
    stmt = stmt.order_by(MailAccount.id.desc()).limit(limit)
    accounts = (await session.execute(stmt)).scalars().all()
    return [_public_account(account, current_user) for account in accounts]


@router.post("", response_model=MailAccountPublic, status_code=status.HTTP_201_CREATED)
async def create_mail_account(
    payload: MailAccountCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MailAccountPublic:
    email = payload.email.strip().lower()
    existing = (
        await session.execute(select(MailAccount).where(MailAccount.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mail account exists")

    if _is_admin(current_user):
        owner_type = payload.owner_type or MailAccountOwnerType.USER
        owner_user_id = payload.owner_user_id
        if owner_type == MailAccountOwnerType.USER and owner_user_id is None:
            owner_user_id = current_user.id
        if owner_type == MailAccountOwnerType.PUBLIC:
            owner_user_id = None
        created_via = "admin"
    else:
        owner_type = MailAccountOwnerType.USER
        owner_user_id = current_user.id
        created_via = "user_web"

    account = MailAccount(
        email=email,
        client_id=payload.client_id,
        refresh_token_encrypted=_cipher().encrypt(payload.refresh_token),
        owner_type=owner_type,
        owner_user_id=owner_user_id,
        status=payload.status,
        default_proxy=payload.default_proxy,
        remark=payload.remark,
        created_by_user_id=current_user.id,
        created_via=created_via,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return _public_account(account, current_user)


@router.get("/{account_id}", response_model=MailAccountPublic)
async def get_mail_account(
    account_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MailAccountPublic:
    account = await _get_visible_account(session, account_id, current_user)
    return _public_account(account, current_user)


@router.patch("/{account_id}", response_model=MailAccountPublic)
async def update_mail_account(
    account_id: int,
    payload: MailAccountUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MailAccountPublic:
    account = await _get_manageable_account(session, account_id, current_user)
    fields = payload.model_fields_set

    if _is_admin(current_user):
        if "owner_type" in fields and payload.owner_type is not None:
            account.owner_type = payload.owner_type
        if "owner_user_id" in fields:
            account.owner_user_id = payload.owner_user_id
        if account.owner_type == MailAccountOwnerType.PUBLIC:
            account.owner_user_id = None
    if "status" in fields and payload.status is not None:
        account.status = payload.status
    if "default_proxy" in fields:
        account.default_proxy = payload.default_proxy
    if "remark" in fields:
        account.remark = payload.remark

    await session.commit()
    await session.refresh(account)
    return _public_account(account, current_user)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mail_account(
    account_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    account = await _get_manageable_account(session, account_id, current_user)
    account.status = MailAccountStatus.DISABLED
    await session.commit()


@router.post("/{account_id}/claim", response_model=MailAccountPublic)
async def claim_mail_account(
    account_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MailAccountPublic:
    account = await _get_visible_account(session, account_id, current_user)
    if account.owner_type != MailAccountOwnerType.PUBLIC:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mail account is not public",
        )

    previous_owner_type = account.owner_type.value
    account.owner_type = MailAccountOwnerType.USER
    account.owner_user_id = current_user.id
    session.add(
        MailAccountClaim(
            mail_account_id=account.id,
            claimed_by_user_id=current_user.id,
            previous_owner_type=previous_owner_type,
        )
    )
    await session.commit()
    await session.refresh(account)
    return _public_account(account, current_user)


@router.get("/{account_id}/credentials", response_model=MailAccountCredentialsPublic)
async def get_mail_account_credentials(
    account_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MailAccountCredentialsPublic:
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    account = await _get_account_or_404(session, account_id)
    refresh_token = _cipher().decrypt(account.refresh_token_encrypted)
    await write_audit_log(
        session,
        actor_user_id=current_user.id,
        action="mail_account.credentials.view",
        target_type="mail_account",
        target_id=str(account.id),
        metadata={"email": account.email},
        ip_address=request.client.host if request.client else None,
    )
    return MailAccountCredentialsPublic(
        client_id=account.client_id,
        refresh_token=refresh_token,
    )


@router.patch("/{account_id}/credentials", response_model=MailAccountPublic)
async def update_mail_account_credentials(
    account_id: int,
    payload: MailAccountCredentialsUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MailAccountPublic:
    account = await _get_manageable_account(session, account_id, current_user)
    fields = payload.model_fields_set
    if "client_id" in fields and payload.client_id is not None:
        account.client_id = payload.client_id
    if "refresh_token" in fields and payload.refresh_token is not None:
        account.refresh_token_encrypted = _cipher().encrypt(payload.refresh_token)
    await session.commit()
    await session.refresh(account)

    if _is_admin(current_user):
        await write_audit_log(
            session,
            actor_user_id=current_user.id,
            action="mail_account.credentials.update",
            target_type="mail_account",
            target_id=str(account.id),
            metadata={"email": account.email},
            ip_address=request.client.host if request.client else None,
        )
    return _public_account(account, current_user)


async def _run_account_operation(
    session: AsyncSession,
    *,
    account: MailAccount,
    current_user: User,
    operation: str,
    mailbox: str,
) -> tuple[str, list[dict[str, Any]]]:
    if account.status != MailAccountStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mail account is disabled")

    credentials = _credentials(account)
    if operation == "clear":
        protocol = await clear_mailbox(credentials, mailbox=mailbox)
        return protocol, []
    items, protocol = await fetch_messages(credentials, mailbox=mailbox, limit=1)
    return protocol, items


@router.post("/{account_id}/test-fetch", response_model=MailAccountTestFetchResponse)
async def test_fetch_mail_account(
    account_id: int,
    mailbox: str = Query(default="INBOX"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MailAccountTestFetchResponse:
    trace_id = uuid4().hex
    started_at = perf_counter()
    account = await _get_manageable_account(session, account_id, current_user)
    try:
        protocol, items = await _run_account_operation(
            session,
            account=account,
            current_user=current_user,
            operation="test_fetch",
            mailbox=mailbox,
        )
        account.last_protocol = protocol
        account.last_success_at = datetime.now(UTC)
        account.last_error_code = None
        await session.commit()
        await write_mail_fetch_log(
            session,
            trace_id=trace_id,
            user_id=current_user.id,
            mail_account_id=account.id,
            email=account.email,
            mailbox=mailbox,
            operation="test_fetch",
            source_protocol=protocol,
            status="success",
            duration_ms=_duration_ms(started_at),
        )
        return MailAccountTestFetchResponse(
            protocol=protocol,
            message_count=len(items),
            trace_id=trace_id,
        )
    except Exception as exc:
        account.last_error_code = "mail_fetch_failed"
        await session.commit()
        await write_mail_fetch_log(
            session,
            trace_id=trace_id,
            user_id=current_user.id,
            mail_account_id=account.id,
            email=account.email,
            mailbox=mailbox,
            operation="test_fetch",
            source_protocol=None,
            status="failed",
            duration_ms=_duration_ms(started_at),
            error_code="mail_fetch_failed",
            error_message=str(exc),
        )
        raise


@router.post("/{account_id}/clear", response_model=MailAccountTestFetchResponse)
async def clear_mail_account(
    account_id: int,
    mailbox: str = Query(default="INBOX"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MailAccountTestFetchResponse:
    trace_id = uuid4().hex
    started_at = perf_counter()
    account = await _get_manageable_account(session, account_id, current_user)
    protocol, items = await _run_account_operation(
        session,
        account=account,
        current_user=current_user,
        operation="clear",
        mailbox=mailbox,
    )
    await write_mail_fetch_log(
        session,
        trace_id=trace_id,
        user_id=current_user.id,
        mail_account_id=account.id,
        email=account.email,
        mailbox=mailbox,
        operation="clear",
        source_protocol=protocol,
        status="success",
        duration_ms=_duration_ms(started_at),
    )
    return MailAccountTestFetchResponse(
        protocol=protocol,
        message_count=len(items),
        trace_id=trace_id,
    )
