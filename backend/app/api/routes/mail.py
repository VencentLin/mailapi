"""Compatible mail fetch API.

POST /api/mail/fetch
  - Authenticated: user-owned account
  - Anonymous: public account
  - Existing account: uses stored credentials
"""

from __future__ import annotations

from dataclasses import asdict
from re import search
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
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
from backend.app.services.mail_fetch_logs import write_mail_fetch_log
from backend.app.services.mail_fetchers import (
    MailCredentials,
    clear_mailbox,
    fetch_mail_for_account,
    fetch_messages,
)
from backend.app.services.users import get_user_by_id

router = APIRouter(tags=["mail"])

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


@router.post("/mail/fetch")
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


def _mail_account_status(result: Any) -> str:
    owner = result.account.owner_type.value
    if result.created:
        return f"auto_created_{owner}"
    return f"existing_{owner}"


def _extract_code(item: dict[str, Any]) -> str | None:
    for key in ("text", "subject"):
        match = search(r"(?<!\d)\d{4,8}(?!\d)", str(item.get(key) or ""))
        if match:
            return match.group(0)
    return None


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    sender = item.get("sender") or item.get("send") or ""
    received_at = item.get("received_at") or item.get("date")
    return {
        "id": item.get("id"),
        "send": sender,
        "sender": sender,
        "subject": item.get("subject") or "",
        "text": item.get("text") or "",
        "html": item.get("html"),
        "date": received_at,
        "received_at": received_at,
        "verification_code": _extract_code(item),
    }


async def _request_payload(request: Request, default_limit: int) -> dict[str, Any]:
    if request.method == "GET":
        return dict(request.query_params)
    body = await request.json()
    if not isinstance(body, dict):
        return {}
    payload = dict(body)
    payload.setdefault("limit", default_limit)
    return payload


def _resolve_payload(payload: dict[str, Any]) -> MailAccountResolve:
    return MailAccountResolve(
        email=str(payload.get("email") or ""),
        client_id=str(payload.get("client_id") or ""),
        refresh_token=str(payload.get("refresh_token") or ""),
    )


def _duration_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


async def _resolve_credentials(
    session: AsyncSession,
    *,
    user: User | None,
    payload: dict[str, Any],
) -> tuple[Any, MailCredentials, str]:
    result = await resolve_or_create_mail_account(
        session,
        user=user,
        resolve=_resolve_payload(payload),
    )
    cipher = TokenCipher(key=get_settings().token_encryption_key)
    refresh_token = cipher.decrypt(result.account.refresh_token_encrypted)
    return (
        result,
        MailCredentials(
            email=result.account.email,
            client_id=result.account.client_id,
            refresh_token=refresh_token,
        ),
        _mail_account_status(result),
    )


async def _compatible_fetch(
    request: Request,
    *,
    operation: str,
    default_limit: int,
    force_limit: int | None = None,
    session: AsyncSession,
    user: User | None,
) -> JSONResponse | dict[str, Any]:
    trace_id = uuid4().hex
    started_at = perf_counter()
    payload = await _request_payload(request, default_limit)
    mailbox = str(payload.get("mailbox") or "INBOX")
    result = None
    try:
        result, credentials, account_status = await _resolve_credentials(
            session,
            user=user,
            payload=payload,
        )
        limit = force_limit or int(payload.get("limit") or default_limit)
        items, protocol = await fetch_messages(
            credentials,
            mailbox=mailbox,
            limit=limit,
        )
        await write_mail_fetch_log(
            session,
            trace_id=trace_id,
            user_id=user.id if user else None,
            mail_account_id=result.account.id,
            email=result.account.email,
            mailbox=mailbox,
            operation=operation,
            source_protocol=protocol,
            status="success",
            duration_ms=_duration_ms(started_at),
        )
        return {
            "code": "200",
            "data": [_public_item(item) for item in items],
            "trace_id": trace_id,
            "protocol": protocol,
            "mail_account_status": account_status,
        }
    except MailAccountNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        email = result.account.email if result is not None else str(payload.get("email") or "")
        account_id = result.account.id if result is not None else None
        await write_mail_fetch_log(
            session,
            trace_id=trace_id,
            user_id=user.id if user else None,
            mail_account_id=account_id,
            email=email,
            mailbox=mailbox,
            operation=operation,
            source_protocol=None,
            status="failed",
            duration_ms=_duration_ms(started_at),
            error_code="mail_fetch_failed",
            error_message=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "code": "502",
                "error": "mail_fetch_failed",
                "message": str(exc),
                "trace_id": trace_id,
            },
        )


@router.api_route("/mail_new", methods=["GET", "POST"], response_model=None)
async def mail_new(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user: User | None = Depends(get_optional_user),
) -> Any:
    return await _compatible_fetch(
        request,
        operation="mail_new",
        default_limit=1,
        force_limit=1,
        session=session,
        user=user,
    )


@router.api_route("/mail_all", methods=["GET", "POST"], response_model=None)
async def mail_all(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user: User | None = Depends(get_optional_user),
) -> Any:
    return await _compatible_fetch(
        request,
        operation="mail_all",
        default_limit=50,
        session=session,
        user=user,
    )


@router.api_route("/process-mailbox", methods=["GET", "POST"], response_model=None)
async def process_mailbox(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user: User | None = Depends(get_optional_user),
) -> Any:
    trace_id = uuid4().hex
    started_at = perf_counter()
    payload = await _request_payload(request, default_limit=1)
    mailbox = str(payload.get("mailbox") or "INBOX")
    result = None
    try:
        result, credentials, account_status = await _resolve_credentials(
            session,
            user=user,
            payload=payload,
        )
        protocol = await clear_mailbox(credentials, mailbox=mailbox)
        await write_mail_fetch_log(
            session,
            trace_id=trace_id,
            user_id=user.id if user else None,
            mail_account_id=result.account.id,
            email=result.account.email,
            mailbox=mailbox,
            operation="process_mailbox",
            source_protocol=protocol,
            status="success",
            duration_ms=_duration_ms(started_at),
        )
        return {
            "code": "200",
            "data": {"message": "邮件正在清空中... 请稍后查看邮件"},
            "trace_id": trace_id,
            "protocol": protocol,
            "mail_account_status": account_status,
        }
    except MailAccountNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        email = result.account.email if result is not None else str(payload.get("email") or "")
        account_id = result.account.id if result is not None else None
        await write_mail_fetch_log(
            session,
            trace_id=trace_id,
            user_id=user.id if user else None,
            mail_account_id=account_id,
            email=email,
            mailbox=mailbox,
            operation="process_mailbox",
            source_protocol=None,
            status="failed",
            duration_ms=_duration_ms(started_at),
            error_code="mail_fetch_failed",
            error_message=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "code": "502",
                "error": "mail_fetch_failed",
                "message": str(exc),
                "trace_id": trace_id,
            },
        )
