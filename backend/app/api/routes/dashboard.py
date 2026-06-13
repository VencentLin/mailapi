from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.routes.auth import get_current_user
from backend.app.db.session import get_db_session
from backend.app.models.api_key import ApiKey
from backend.app.models.enums import MailAccountOwnerType, UserRole
from backend.app.models.logs import MailFetchLog
from backend.app.models.mail_account import MailAccount
from backend.app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def _count(session: AsyncSession, stmt) -> int:
    result = await session.execute(stmt)
    return int(result.scalar_one())


@router.get("")
async def get_dashboard(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    data: dict[str, Any] = {
        "my_mail_accounts": await _count(
            session,
            select(func.count(MailAccount.id)).where(
                MailAccount.owner_type == MailAccountOwnerType.USER,
                MailAccount.owner_user_id == current_user.id,
            ),
        ),
        "public_mail_accounts": await _count(
            session,
            select(func.count(MailAccount.id)).where(
                MailAccount.owner_type == MailAccountOwnerType.PUBLIC,
            ),
        ),
        "today_fetches": await _count(
            session,
            select(func.count(MailFetchLog.id)).where(
                MailFetchLog.user_id == current_user.id,
                MailFetchLog.created_at >= today_start,
            ),
        ),
        "today_failed_fetches": await _count(
            session,
            select(func.count(MailFetchLog.id)).where(
                MailFetchLog.user_id == current_user.id,
                MailFetchLog.status == "failed",
                MailFetchLog.created_at >= today_start,
            ),
        ),
    }

    recent_errors = (
        await session.execute(
            select(MailFetchLog)
            .where(MailFetchLog.status == "failed")
            .order_by(MailFetchLog.id.desc())
            .limit(5)
        )
    ).scalars().all()
    if current_user.role != UserRole.ADMIN:
        recent_errors = [item for item in recent_errors if item.user_id == current_user.id]
    data["recent_errors"] = [
        {
            "trace_id": item.trace_id,
            "email": item.email,
            "error_code": item.error_code,
            "error_message": item.error_message,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in recent_errors[:5]
    ]

    if current_user.role == UserRole.ADMIN:
        data.update(
            {
                "global_users": await _count(session, select(func.count(User.id))),
                "global_mail_accounts": await _count(
                    session,
                    select(func.count(MailAccount.id)),
                ),
                "global_api_keys": await _count(session, select(func.count(ApiKey.id))),
                "global_today_fetches": await _count(
                    session,
                    select(func.count(MailFetchLog.id)).where(
                        MailFetchLog.created_at >= today_start,
                    ),
                ),
                "global_today_failed_fetches": await _count(
                    session,
                    select(func.count(MailFetchLog.id)).where(
                        MailFetchLog.status == "failed",
                        MailFetchLog.created_at >= today_start,
                    ),
                ),
            }
        )

    return data
