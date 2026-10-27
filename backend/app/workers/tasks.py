from datetime import UTC, datetime, timedelta
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.analyse import Analyse, StatutAnalyse
from app.models.document import Document
from app.models.dossier import Dossier
from app.services.classifier import classify_piece
from app.services.constitutional import load_articles
from app.services.checklist import (
    check_avocat_presence,
    check_garde_a_vue,
    check_notification_droits,
    check_pieces_obligatoires,
)
from app.services.extraction import extract_text
from app.services.llm_engine import build_prompt, call_llm, retry_with_feedback
from app.services.ner import extract_entities, extract_legal_entities
from app.storage.minio_client import get_minio_client


@shared_task(bind=True, max_retries=2)
def extract_document_task(self, document_id: str) -> None:
    import asyncio

    asyncio.run(_extract_document(UUID(document_id)))


async def _extract_document(document_id: UUID) -> None:
    async with async_session_maker() as db:
        document = await db.get(Document, document_id)
        if document is None:
            return
        try:
            from app.core.config import get_settings

            response = get_minio_client().get_object(get_settings().minio_bucket, document.file_key)
            try:
                data = response.read()
            finally:
                response.close()
                response.release_conn()
            document.extracted_text = extract_text(data, document.mime_type)
            document.type_piece = classify_piece(document.extracted_text, document.filename)
            document.extraction_status = "done"
        except Exception:
            document.extraction_status = "failed"
        await db.commit()


@shared_task
def run_analysis_task(analyse_id: str) -> None:
    import asyncio

    asyncio.run(_run_analysis(UUID(analyse_id)))


async def _run_analysis(analyse_id: UUID) -> None:
    async with async_session_maker() as db:
        analyse = await db.get(Analyse, analyse_id)
        if analyse is None:
            return
        analyse.statut = StatutAnalyse.RUNNING
        await db.commit()
        try:
            articles = load_articles()
        except Exception:
            articles = []
        if not articles:
            analyse.statut = StatutAnalyse.ERROR
            analyse.error_message = (
                "Analyse suspendue : le registre constitutionnel officiel est vide. "
                "Aucune conclusion juridique n'a été générée."
            )
            analyse.finished_at = datetime.now(UTC)
            await db.commit()
            return
        dossier = await db.get(Dossier, analyse.dossier_id)
        if dossier is None:
            analyse.statut = StatutAnalyse.ERROR
            analyse.error_message = "Dossier associé introuvable."
            analyse.finished_at = datetime.now(UTC)
            await db.commit()
            return
        documents = list(
            await db.scalars(
                select(Document).where(Document.dossier_id == dossier.id, Document.deleted_at.is_(None))
            )
        )
        pending_documents = [document for document in documents if document.extraction_status == "pending"]
        if pending_documents:
            analyse.statut = StatutAnalyse.ERROR
            analyse.error_message = "Analyse suspendue : l'extraction d'une ou plusieurs pièces n'est pas terminée."
            analyse.finished_at = datetime.now(UTC)
            await db.commit()
            return
        try:
            controls = []
            for rule in (check_garde_a_vue, check_notification_droits, check_avocat_presence):
                control = rule(documents, articles)
                if control is not None:
                    controls.append(control)
            controls.extend(check_pieces_obligatoires(dossier.infraction_type, documents, articles))
            from app.services.validator import validate_analyse_resultat

            extracted_documents = [
                {
                    "nom": document.filename,
                    "type": document.type_piece.value,
                    "texte": document.extracted_text or "",
                }
                for document in documents
                if document.extraction_status == "done"
            ]
            all_text = "\n".join(item["texte"] for item in extracted_documents)
            entities = {
                "personnes_dates_lieux": extract_entities(all_text),
                "references_legales": extract_legal_entities(all_text),
                "documents_en_echec_extraction": sum(
                    document.extraction_status == "failed" for document in documents
                ),
            }
            article_context = [
                {"numero": item.numero, "alinea": item.alinea or "", "texte": item.texte, "theme": item.theme}
                for item in articles
            ]
            messages = build_prompt(
                {
                    "numero_dossier": dossier.numero_dossier,
                    "infraction_type": dossier.infraction_type,
                    "date_ouverture": dossier.date_ouverture.isoformat(),
                },
                extracted_documents,
                entities,
                article_context,
            )
            validation_error = ""
            result = None
            for attempt in range(3):
                try:
                    model_result = await call_llm(messages)
                    model_controls = model_result.get("controles_procedure", [])
                    result_data = {
                        **model_result,
                        "statut_global": "A_VERIFIER_PAR_UNE_AUTORITE_COMPETENTE",
                        "synthese": {
                            **model_result.get("synthese", {}),
                            "pieces_analysees": len(extracted_documents),
                            "alertes_procedurales": len(controls) + len(model_controls),
                            "pieces_manquantes": sum(
                                control.code == "PIECES_OBLIGATOIRES_MANQUANTES" for control in controls
                            ),
                            "documents_en_echec_extraction": entities["documents_en_echec_extraction"],
                        },
                        "controles_procedure": [control.model_dump(mode="json") for control in controls]
                        + model_controls,
                    }
                    result = validate_analyse_resultat(result_data, articles)
                    break
                except Exception as error:
                    validation_error = str(error)
                    if attempt < 2:
                        messages = retry_with_feedback(str(locals().get("model_result", {})), validation_error)
            if result is None:
                raise RuntimeError(f"Validation de l'analyse impossible après 2 corrections : {validation_error}")
        except Exception as error:
            analyse.statut = StatutAnalyse.ERROR
            analyse.error_message = str(error)[:1000]
            analyse.finished_at = datetime.now(UTC)
            await db.commit()
            return
        analyse.resultat = result.model_dump(mode="json")
        analyse.statut = StatutAnalyse.DONE
        analyse.error_message = None
        analyse.finished_at = datetime.now(UTC)
        await db.commit()


@shared_task
def generate_report_task(analyse_id: str) -> None:
    return None


@shared_task
def purge_old_documents_task() -> None:
    import asyncio

    asyncio.run(_purge_old_documents())


async def _purge_old_documents() -> None:
    cutoff = datetime.now(UTC) - timedelta(days=365 * 5)
    async with async_session_maker() as db:
        documents = await db.scalars(
            select(Document).where(Document.uploaded_at < cutoff, Document.deleted_at.is_(None))
        )
        for document in documents:
            document.deleted_at = datetime.now(UTC)
        await db.commit()


@shared_task
def reindex_constitution_task() -> None:
    return None