from datetime import datetime
from uuid import UUID

from app.models.document import TypePiece
from app.schemas.common import ORMModel


class DocumentRead(ORMModel):
    id: UUID
    dossier_id: UUID
    filename: str
    type_piece: TypePiece
    file_hash_sha256: str
    mime_type: str
    size_bytes: int
    extraction_status: str
    uploaded_at: datetime


class DocumentUploadResponse(DocumentRead):
    task_id: str | None = None


class DocumentList(ORMModel):
    items: list[DocumentRead]