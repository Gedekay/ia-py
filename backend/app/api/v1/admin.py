from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.dependencies import DbSession, require_role
from app.models.analyse import Analyse, StatutAnalyse
from app.models.audit_log import AuditLog
from app.models.dossier import Dossier
from app.models.user import Role, User
from app.services.audit import log_action
from app.workers.tasks import reindex_constitution_task


router = APIRouter(prefix="/admin", tags=["admin"])
AdminUser = Annotated[User, Depends(require_role([Role.ADMIN]))]


@router.get("/audit")
async def list_audit_logs(
    db: DbSession,
    _: AdminUser,
    page: int = 1,
    size: int = 50,
) -> list[dict[str, object]]:
    size = min(max(size, 1), 100)
    page = max(page, 1)
    entries = await db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()).offset((page - 1) * size).limit(size))
    return [
        {"id": row.id, "user_id": row.user_id, "action": row.action, "resource_type": row.resource_type,
         "resource_id": row.resource_id, "ip_address": row.ip_address, "timestamp": row.timestamp}
        for row in entries
    ]


@router.get("/metrics")
async def get_metrics(db: DbSession, _: AdminUser) -> dict[str, int]:
    dossiers = await db.scalar(select(func.count()).select_from(Dossier)) or 0
    analyses = await db.scalar(select(func.count()).select_from(Analyse)) or 0
    failed_analyses = await db.scalar(
        select(func.count()).select_from(Analyse).where(Analyse.statut == StatutAnalyse.ERROR)
    ) or 0
    return {"dossiers": dossiers, "analyses": analyses, "analyses_en_erreur": failed_analyses}


@router.post("/constitution/reload", status_code=202)
async def reload_constitution(_: AdminUser) -> dict[str, str]:
    task = reindex_constitution_task.delay()
    return {"task_id": task.id, "status": "queued"}