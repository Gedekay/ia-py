from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from app.core.config import get_settings
from app.core.dependencies import DbSession, get_current_user, require_role
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.document import Document, TypePiece
from app.models.dossier import Dossier
from app.models.user import Role, User
from app.schemas.document import DocumentRead, DocumentUploadResponse
from app.services.audit import log_action
from app.services.extraction import SUPPORTED_MIME_TYPES
from app.storage.minio_client import delete_file, ensure_bucket, get_presigned_url, upload_file
from app.workers.tasks import extract_document_task


router = APIRouter(tags=["documents"])
Investigator = Annotated[User, Depends(require_role([Role.ENQUETEUR, Role.ADMIN]))]
Reader = Annotated[User, Depends(get_current_user)]


async def _get_dossier(dossier_id: UUID, db: DbSession, user: User) -> Dossier:
    dossier = await db.get(Dossier, dossier_id)
    if dossier is None:
        raise NotFoundError("Dossier introuvable.")
    if user.role == Role.ENQUETEUR and dossier.created_by_id != user.id:
        raise ForbiddenError()
    return dossier


@router.post("/dossiers/{dossier_id}/documents", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    dossier_id: UUID,
    request: Request,
    db: DbSession,
    user: Investigator,
    file: Annotated[UploadFile, File()],
) -> DocumentUploadResponse:
    await _get_dossier(dossier_id, db, user)
    mime = file.content_type or "application/octet-stream"
    if mime not in SUPPORTED_MIME_TYPES:
        raise ValidationError("Format accepté : PDF, DOCX, TXT, JPEG, PNG ou TIFF.")
    data = await file.read(get_settings().max_upload_size_bytes + 1)
    if not data or len(data) > get_settings().max_upload_size_bytes:
        raise ValidationError("Fichier vide ou taille maximale dépassée.")
    file_id = uuid4()
    key = f"{dossier_id}/{file_id}"
    await run_in_threadpool(ensure_bucket)
    await run_in_threadpool(upload_file, key, data, mime)
    document = Document(
        dossier_id=dossier_id,
        filename=(file.filename or "document")[:255],
        type_piece=TypePiece.AUTRE,
        file_key=key,
        file_hash_sha256=sha256(data).hexdigest(),
        mime_type=mime,
        size_bytes=len(data),
        uploaded_by_id=user.id,
    )
    db.add(document)
    await db.flush()
    await log_action(db, user, "DOCUMENT_UPLOADED", "document", document.id, request.client.host if request.client else None)
    await db.commit()
    await db.refresh(document)
    task = extract_document_task.delay(str(document.id))
    return DocumentUploadResponse.model_validate({**document.__dict__, "task_id": task.id})


@router.get("/dossiers/{dossier_id}/documents", response_model=list[DocumentRead])
async def list_documents(dossier_id: UUID, db: DbSession, user: Reader) -> list[Document]:
    await _get_dossier(dossier_id, db, user)
    return list(await db.scalars(select(Document).where(Document.dossier_id == dossier_id, Document.deleted_at.is_(None))))


@router.get("/documents/{document_id}", response_model=DocumentRead)
async def get_document(document_id: UUID, db: DbSession, user: Reader) -> Document:
    document = await db.get(Document, document_id)
    if document is None or document.deleted_at is not None:
        raise NotFoundError("Document introuvable.")
    await _get_dossier(document.dossier_id, db, user)
    return document


@router.get("/documents/{document_id}/download")
async def download_document(document_id: UUID, db: DbSession, user: Reader) -> dict[str, str]:
    document = await get_document(document_id, db, user)
    url = await run_in_threadpool(get_presigned_url, document.file_key, 300)
    return {"url": url, "expires_in_seconds": "300"}


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: UUID, db: DbSession, user: Investigator) -> None:
    document = await db.get(Document, document_id)
    if document is None or document.deleted_at is not None:
        raise NotFoundError("Document introuvable.")
    await _get_dossier(document.dossier_id, db, user)
    document.deleted_at = datetime.now(UTC)
    await log_action(db, user, "DOCUMENT_DELETED", "document", document.id)
    await db.commit()
    await run_in_threadpool(delete_file, document.file_key)