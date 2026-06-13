from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.logs import MailFetchLog


async def write_mail_fetch_log(
    session: AsyncSession,
    *,
    trace_id: str,
    user_id: int | None,
    mail_account_id: int | None,
    email: str,
    mailbox: str,
    operation: str,
    source_protocol: str | None,
    status: str,
    duration_ms: int,
    error_code: str | None = None,
    error_message: str | None = None,
) -> MailFetchLog:
    log = MailFetchLog(
        trace_id=trace_id,
        user_id=user_id,
        api_key_id=None,
        mail_account_id=mail_account_id,
        email=email,
        mailbox=mailbox,
        operation=operation,
        source_protocol=source_protocol,
        status=status,
        error_code=error_code,
        error_message=error_message,
        duration_ms=duration_ms,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log
