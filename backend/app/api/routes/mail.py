"""Compatible mail fetch API.

POST /api/mail/fetch
  - Authenticated: user-owned account
  - Anonymous: public account
  - Existing account: uses stored credentials
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
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
from backend.app.services.api_keys import ApiKeyAuthError, verify_api_key
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


@dataclass(frozen=True)
class MailRequestAuth:
    user: User | None
    api_key_id: int | None = None


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User | None:
    """Return the authenticated user, or None if no valid token is present."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    token = credentials.credentials.strip()
    try:
        payload = decode_access_token(token)
    except ValueError:
        try:
            verified = await verify_api_key(session, token, required_scope="mail:fetch")
        except ApiKeyAuthError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail={"error_code": exc.error_code, "message": exc.message},
            ) from exc
        return verified.user
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


async def _resolve_auth_context(
    session: AsyncSession,
    request: Request,
    payload: dict[str, Any],
) -> MailRequestAuth:
    user_token = str(payload.get("user_token") or "").strip()
    if user_token:
        verified = await verify_api_key(session, user_token, required_scope="mail:fetch")
        return MailRequestAuth(user=verified.user, api_key_id=verified.api_key.id)

    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    if not authorization:
        return MailRequestAuth(user=None)

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return MailRequestAuth(user=None)

    bearer_token = token.strip()
    try:
        jwt_payload = decode_access_token(bearer_token)
    except ValueError:
        verified = await verify_api_key(session, bearer_token, required_scope="mail:fetch")
        return MailRequestAuth(user=verified.user, api_key_id=verified.api_key.id)

    subject = jwt_payload.get("sub")
    if not subject:
        raise ApiKeyAuthError("INVALID_ACCESS_TOKEN", "Invalid access token.")
    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise ApiKeyAuthError("INVALID_ACCESS_TOKEN", "Invalid access token.") from exc

    user = await get_user_by_id(session, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise ApiKeyAuthError("INVALID_ACCESS_TOKEN", "Inactive or unknown user.")
    return MailRequestAuth(user=user)


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


def _contains(value: Any, needle: str | None) -> bool:
    if not needle:
        return True
    return needle.lower() in str(value or "").lower()


def _parse_received_at(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _matches_since(value: Any, since_minutes: int | None) -> bool:
    if not since_minutes:
        return True
    received_at = _parse_received_at(value)
    if received_at is None:
        return True
    return received_at >= datetime.now(UTC) - timedelta(minutes=since_minutes)


def _compile_code_pattern(pattern_text: Any) -> re.Pattern[str]:
    pattern = str(pattern_text or r"(?<!\d)\d{4,8}(?!\d)")
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid regex: {exc}",
        ) from exc


def _match_verification_item(
    item: dict[str, Any],
    payload: dict[str, Any],
    pattern: re.Pattern[str],
) -> tuple[dict[str, Any], str] | None:
    sender = item.get("sender") or item.get("send")
    subject = item.get("subject") or ""
    text = item.get("text") or ""
    html = item.get("html") or ""
    body = f"{text}\n{html}"

    if not _contains(sender, str(payload.get("sender") or "") or None):
        return None
    if not _contains(subject, str(payload.get("subject_keyword") or "") or None):
        return None
    if not _contains(body, str(payload.get("body_keyword") or "") or None):
        return None
    received_at = item.get("received_at") or item.get("date")
    since_minutes = _optional_int(payload.get("since_minutes"))
    if not _matches_since(received_at, since_minutes):
        return None

    for candidate in (text, subject, html):
        match = pattern.search(str(candidate or ""))
        if match:
            return item, match.group(0)
    return None


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


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


async def _resolve_credentials(
    session: AsyncSession,
    *,
    auth: MailRequestAuth,
    payload: dict[str, Any],
) -> tuple[Any, MailCredentials, str]:
    result = await resolve_or_create_mail_account(
        session,
        user=auth.user,
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
) -> JSONResponse | dict[str, Any]:
    trace_id = uuid4().hex
    started_at = perf_counter()
    payload = await _request_payload(request, default_limit)
    mailbox = str(payload.get("mailbox") or "INBOX")
    result = None
    auth_context = MailRequestAuth(user=None)
    try:
        auth_context = await _resolve_auth_context(session, request, payload)
        result, credentials, account_status = await _resolve_credentials(
            session,
            auth=auth_context,
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
            user_id=auth_context.user.id if auth_context.user else None,
            mail_account_id=result.account.id,
            email=result.account.email,
            mailbox=mailbox,
            operation=operation,
            source_protocol=protocol,
            status="success",
            duration_ms=_duration_ms(started_at),
            api_key_id=auth_context.api_key_id,
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
    except ApiKeyAuthError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": str(exc.status_code),
                "error_code": exc.error_code,
                "message": exc.message,
                "trace_id": trace_id,
            },
        )
    except Exception as exc:
        email = result.account.email if result is not None else str(payload.get("email") or "")
        account_id = result.account.id if result is not None else None
        await write_mail_fetch_log(
            session,
            trace_id=trace_id,
            user_id=auth_context.user.id if auth_context.user else None,
            mail_account_id=account_id,
            email=email,
            mailbox=mailbox,
            operation=operation,
            source_protocol=None,
            status="failed",
            duration_ms=_duration_ms(started_at),
            error_code="mail_fetch_failed",
            error_message=str(exc),
            api_key_id=auth_context.api_key_id,
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
) -> Any:
    return await _compatible_fetch(
        request,
        operation="mail_new",
        default_limit=1,
        force_limit=1,
        session=session,
    )


@router.api_route("/mail_all", methods=["GET", "POST"], response_model=None)
async def mail_all(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    return await _compatible_fetch(
        request,
        operation="mail_all",
        default_limit=50,
        session=session,
    )


@router.api_route("/process-mailbox", methods=["GET", "POST"], response_model=None)
async def process_mailbox(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    trace_id = uuid4().hex
    started_at = perf_counter()
    payload = await _request_payload(request, default_limit=1)
    mailbox = str(payload.get("mailbox") or "INBOX")
    result = None
    auth_context = MailRequestAuth(user=None)
    try:
        auth_context = await _resolve_auth_context(session, request, payload)
        result, credentials, account_status = await _resolve_credentials(
            session,
            auth=auth_context,
            payload=payload,
        )
        protocol = await clear_mailbox(credentials, mailbox=mailbox)
        await write_mail_fetch_log(
            session,
            trace_id=trace_id,
            user_id=auth_context.user.id if auth_context.user else None,
            mail_account_id=result.account.id,
            email=result.account.email,
            mailbox=mailbox,
            operation="process_mailbox",
            source_protocol=protocol,
            status="success",
            duration_ms=_duration_ms(started_at),
            api_key_id=auth_context.api_key_id,
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
    except ApiKeyAuthError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": str(exc.status_code),
                "error_code": exc.error_code,
                "message": exc.message,
                "trace_id": trace_id,
            },
        )
    except Exception as exc:
        email = result.account.email if result is not None else str(payload.get("email") or "")
        account_id = result.account.id if result is not None else None
        await write_mail_fetch_log(
            session,
            trace_id=trace_id,
            user_id=auth_context.user.id if auth_context.user else None,
            mail_account_id=account_id,
            email=email,
            mailbox=mailbox,
            operation="process_mailbox",
            source_protocol=None,
            status="failed",
            duration_ms=_duration_ms(started_at),
            error_code="mail_fetch_failed",
            error_message=str(exc),
            api_key_id=auth_context.api_key_id,
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


@router.post("/verification-code", response_model=None)
async def verification_code(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    trace_id = uuid4().hex
    started_at = perf_counter()
    payload = await _request_payload(request, default_limit=20)
    mailbox = str(payload.get("mailbox") or "INBOX")
    result = None
    auth_context = MailRequestAuth(user=None)

    try:
        pattern = _compile_code_pattern(payload.get("regex"))
        auth_context = await _resolve_auth_context(session, request, payload)
        result, credentials, account_status = await _resolve_credentials(
            session,
            auth=auth_context,
            payload=payload,
        )
        limit = int(payload.get("limit") or 20)
        items, protocol = await fetch_messages(credentials, mailbox=mailbox, limit=limit)

        matched_item: dict[str, Any] | None = None
        matched_code: str | None = None
        for item in items:
            match = _match_verification_item(item, payload, pattern)
            if match is not None:
                matched_item, matched_code = match
                break

        if matched_item is None or matched_code is None:
            await write_mail_fetch_log(
                session,
                trace_id=trace_id,
                user_id=auth_context.user.id if auth_context.user else None,
                mail_account_id=result.account.id,
                email=result.account.email,
                mailbox=mailbox,
                operation="verification_code",
                source_protocol=protocol,
                status="failed",
                duration_ms=_duration_ms(started_at),
                error_code="VERIFICATION_CODE_NOT_FOUND",
                error_message="No verification code matched the request filters.",
                api_key_id=auth_context.api_key_id,
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "code": "404",
                    "error_code": "VERIFICATION_CODE_NOT_FOUND",
                    "message": "No verification code matched the request filters.",
                    "trace_id": trace_id,
                },
            )

        if payload.get("delete_after_fetch") is True:
            await clear_mailbox(credentials, mailbox=mailbox)

        await write_mail_fetch_log(
            session,
            trace_id=trace_id,
            user_id=auth_context.user.id if auth_context.user else None,
            mail_account_id=result.account.id,
            email=result.account.email,
            mailbox=mailbox,
            operation="verification_code",
            source_protocol=protocol,
            status="success",
            duration_ms=_duration_ms(started_at),
            api_key_id=auth_context.api_key_id,
        )
        return {
            "code": "200",
            "verification_code": matched_code,
            "matched_email": _public_item(matched_item),
            "source_protocol": protocol,
            "mail_account_status": account_status,
            "trace_id": trace_id,
        }
    except MailAccountNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ApiKeyAuthError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": str(exc.status_code),
                "error_code": exc.error_code,
                "message": exc.message,
                "trace_id": trace_id,
            },
        )
    except Exception as exc:
        email = result.account.email if result is not None else str(payload.get("email") or "")
        account_id = result.account.id if result is not None else None
        await write_mail_fetch_log(
            session,
            trace_id=trace_id,
            user_id=auth_context.user.id if auth_context.user else None,
            mail_account_id=account_id,
            email=email,
            mailbox=mailbox,
            operation="verification_code",
            source_protocol=None,
            status="failed",
            duration_ms=_duration_ms(started_at),
            error_code="mail_fetch_failed",
            error_message=str(exc),
            api_key_id=auth_context.api_key_id,
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "code": "502",
                "error_code": "mail_fetch_failed",
                "message": str(exc),
                "trace_id": trace_id,
            },
        )
