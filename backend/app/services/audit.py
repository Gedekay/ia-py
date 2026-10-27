from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User


async def log_action(
    db: AsyncSession,
    user: User | None,
    action: str,
    resource_type: str,
    resource_id: str | UUID | None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, str | int | bool] | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user.id if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_=metadata or {},
    )
    db.add(entry)
    await db.flush()
    return entry


async def log_analysis_access(db: AsyncSession, user: User, analyse_id: UUID) -> AuditLog:
    return await log_action(db, user, "ANALYSIS_ACCESS", "analyse", analyse_id)


async def get_user_activity(
    db: AsyncSession, user_id: UUID, from_: datetime, to_: datetime
) -> list[AuditLog]:
    result = await db.scalars(
        select(AuditLog)
        .where(AuditLog.user_id == user_id, AuditLog.timestamp >= from_, AuditLog.timestamp <= to_)
        .order_by(AuditLog.timestamp.desc())
    )
    return list(result)