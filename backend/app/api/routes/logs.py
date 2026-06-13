from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.routes.auth import get_current_user
from backend.app.db.session import get_db_session
from backend.app.models.enums import UserRole
from backend.app.models.logs import AuditLog, MailFetchLog
from backend.app.models.user import User
from backend.app.schemas.logs import AuditLogPublic, MailFetchLogPublic

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/mail-fetch", response_model=list[MailFetchLogPublic])
async def list_mail_fetch_logs(
    email: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    user_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[MailFetchLogPublic]:
    stmt = select(MailFetchLog)
    if current_user.role != UserRole.ADMIN:
        stmt = stmt.where(MailFetchLog.user_id == current_user.id)
    elif user_id is not None:
        stmt = stmt.where(MailFetchLog.user_id == user_id)
    if email:
        stmt = stmt.where(MailFetchLog.email.ilike(f"%{email.strip().lower()}%"))
    if status_filter:
        stmt = stmt.where(MailFetchLog.status == status_filter)
    stmt = stmt.order_by(MailFetchLog.id.desc()).limit(limit)
    logs = (await session.execute(stmt)).scalars().all()
    return [MailFetchLogPublic.model_validate(log) for log in logs]


@router.get(
    "/audit",
    response_model=list[AuditLogPublic],
    status_code=status.HTTP_200_OK,
)
async def list_audit_logs(
    action: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[AuditLogPublic]:
    if current_user.role != UserRole.ADMIN:
        return []
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.id.desc()).limit(limit)
    logs = (await session.execute(stmt)).scalars().all()
    return [AuditLogPublic.model_validate(log) for log in logs]
