from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from app.core.dependencies import DbSession, get_current_user, require_role
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.analyse import Analyse, StatutAnalyse
from app.models.dossier import Dossier, StatutDossier
from app.models.document import Document
from app.models.user import Role, User
from app.schemas.analyse import AnalyseCreateResponse, AnalyseRead
from app.services.audit import log_action, log_analysis_access
from app.services.report import generate_json_export, generate_pdf
from app.workers.tasks import run_analysis_task


router = APIRouter(tags=["analyses"])
Investigator = Annotated[User, Depends(require_role([Role.ENQUETEUR, Role.ADMIN]))]
Reader = Annotated[User, Depends(get_current_user)]


async def _get_analysis(analyse_id: UUID, db: DbSession, user: User) -> Analyse:
    analyse = await db.get(Analyse, analyse_id)
    if analyse is None:
        raise NotFoundError("Analyse introuvable.")
    dossier = await db.get(Dossier, analyse.dossier_id)
    if dossier is None:
        raise NotFoundError("Dossier introuvable.")
    if user.role == Role.ENQUETEUR and dossier.created_by_id != user.id:
        raise ForbiddenError()
    return analyse


@router.post("/dossiers/{dossier_id}/analyses", response_model=AnalyseCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(dossier_id: UUID, db: DbSession, user: Investigator) -> AnalyseCreateResponse:
    dossier = await db.get(Dossier, dossier_id)
    if dossier is None:
        raise NotFoundError("Dossier introuvable.")
    if user.role == Role.ENQUETEUR and dossier.created_by_id != user.id:
        raise ForbiddenError()
    if dossier.statut == StatutDossier.CLOS:
        raise ValidationError("Un dossier clos ne peut pas être analysé.")
    documents = await db.scalars(
        select(Document).where(Document.dossier_id == dossier_id, Document.deleted_at.is_(None))
    )
    if not list(documents):
        raise ValidationError("Ajoutez au moins une pièce avant de lancer l'analyse.")
    analyse = Analyse(dossier_id=dossier_id, created_by_id=user.id, statut=StatutAnalyse.PENDING)
    db.add(analyse)
    dossier.statut = StatutDossier.EN_ANALYSE
    await db.flush()
    await log_action(db, user, "ANALYSIS_STARTED", "analyse", analyse.id)
    await db.commit()
    task = run_analysis_task.delay(str(analyse.id))
    return AnalyseCreateResponse(analyse_id=analyse.id, statut=analyse.statut)


@router.get("/analyses/{analyse_id}", response_model=AnalyseRead)
async def get_analysis(analyse_id: UUID, db: DbSession, user: Reader) -> Analyse:
    analyse = await _get_analysis(analyse_id, db, user)
    await log_analysis_access(db, user, analyse.id)
    await db.commit()
    return analyse


@router.get("/dossiers/{dossier_id}/analyses", response_model=list[AnalyseRead])
async def list_analyses(dossier_id: UUID, db: DbSession, user: Reader) -> list[Analyse]:
    dossier = await db.get(Dossier, dossier_id)
    if dossier is None:
        raise NotFoundError("Dossier introuvable.")
    if user.role == Role.ENQUETEUR and dossier.created_by_id != user.id:
        raise ForbiddenError()
    return list(await db.scalars(select(Analyse).where(Analyse.dossier_id == dossier_id).order_by(Analyse.created_at.desc())))


@router.get("/analyses/{analyse_id}/report.json")
async def export_json(analyse_id: UUID, db: DbSession, user: Reader) -> dict[str, object]:
    analyse = await _get_analysis(analyse_id, db, user)
    if analyse.statut != StatutAnalyse.DONE or analyse.resultat is None:
        raise ValidationError("Le rapport n'est pas disponible : l'analyse n'est pas terminée.")
    from app.schemas.analyse import AnalyseResultat

    await log_action(db, user, "ANALYSIS_EXPORTED_JSON", "analyse", analyse.id)
    await db.commit()
    return generate_json_export(AnalyseResultat.model_validate(analyse.resultat), user.email)


@router.get("/analyses/{analyse_id}/report.pdf")
async def export_pdf(analyse_id: UUID, db: DbSession, user: Reader) -> Response:
    analyse = await _get_analysis(analyse_id, db, user)
    if analyse.statut != StatutAnalyse.DONE or analyse.resultat is None:
        raise ValidationError("Le rapport n'est pas disponible : l'analyse n'est pas terminée.")
    from app.schemas.analyse import AnalyseResultat

    await log_action(db, user, "ANALYSIS_EXPORTED_PDF", "analyse", analyse.id)
    await db.commit()
    pdf = await run_in_threadpool(generate_pdf, AnalyseResultat.model_validate(analyse.resultat), user.email)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="rapport-{analyse.id}.pdf"'})