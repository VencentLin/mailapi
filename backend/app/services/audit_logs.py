from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.logs import AuditLog


async def write_audit_log(
    session: AsyncSession,
    *,
    actor_user_id: int | None,
    action: str,
    target_type: str,
    target_id: str,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=metadata,
        ip_address=ip_address,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log
