from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select

from app.core.dependencies import DbSession, get_current_user, require_role
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.dossier import Dossier, StatutDossier
from app.models.user import Role, User
from app.schemas.dossier import DossierCreate, DossierRead, DossierUpdate
from app.services.audit import log_action


router = APIRouter(prefix="/dossiers", tags=["dossiers"])
Investigator = Annotated[User, Depends(require_role([Role.ENQUETEUR, Role.ADMIN]))]
DossierReader = Annotated[User, Depends(get_current_user)]


def _check_access(dossier: Dossier, user: User) -> None:
    if user.role == Role.ENQUETEUR and dossier.created_by_id != user.id:
        raise ForbiddenError()


@router.get("", response_model=list[DossierRead])
async def list_dossiers(
    db: DbSession,
    user: DossierReader,
    statut: StatutDossier | None = None,
    infraction_type: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> list[Dossier]:
    statement = select(Dossier)
    if user.role == Role.ENQUETEUR:
        statement = statement.where(Dossier.created_by_id == user.id)
    if statut:
        statement = statement.where(Dossier.statut == statut)
    if infraction_type:
        statement = statement.where(Dossier.infraction_type == infraction_type)
    statement = statement.order_by(Dossier.created_at.desc()).offset((page - 1) * size).limit(size)
    return list(await db.scalars(statement))


@router.post("", response_model=DossierRead, status_code=status.HTTP_201_CREATED)
async def create_dossier(payload: DossierCreate, request: Request, db: DbSession, user: Investigator) -> Dossier:
    dossier = Dossier(
        numero_dossier=payload.numero_dossier,
        date_ouverture=payload.date_ouverture,
        infraction_type=payload.infraction_type,
        metadata_=payload.metadata_,
        created_by_id=user.id,
    )
    db.add(dossier)
    await db.flush()
    await log_action(db, user, "DOSSIER_CREATED", "dossier", dossier.id, request.client.host if request.client else None)
    await db.commit()
    await db.refresh(dossier)
    return dossier


@router.get("/{dossier_id}", response_model=DossierRead)
async def get_dossier(dossier_id: UUID, db: DbSession, user: DossierReader) -> Dossier:
    dossier = await db.get(Dossier, dossier_id)
    if dossier is None:
        raise NotFoundError("Dossier introuvable.")
    _check_access(dossier, user)
    return dossier


@router.patch("/{dossier_id}", response_model=DossierRead)
async def update_dossier(dossier_id: UUID, payload: DossierUpdate, db: DbSession, user: Investigator) -> Dossier:
    dossier = await db.get(Dossier, dossier_id)
    if dossier is None:
        raise NotFoundError("Dossier introuvable.")
    _check_access(dossier, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dossier, field, value)
    await log_action(db, user, "DOSSIER_UPDATED", "dossier", dossier.id)
    await db.commit()
    await db.refresh(dossier)
    return dossier


@router.post("/{dossier_id}/close", response_model=DossierRead)
async def close_dossier(dossier_id: UUID, db: DbSession, user: Investigator) -> Dossier:
    dossier = await db.get(Dossier, dossier_id)
    if dossier is None:
        raise NotFoundError("Dossier introuvable.")
    _check_access(dossier, user)
    dossier.statut = StatutDossier.CLOS
    await log_action(db, user, "DOSSIER_CLOSED", "dossier", dossier.id)
    await db.commit()
    await db.refresh(dossier)
    return dossier