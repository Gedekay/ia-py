from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdTimestampMixin

if TYPE_CHECKING:
    from app.models.dossier import Dossier


class TypePiece(StrEnum):
    PROCES_VERBAL = "PROCES_VERBAL"
    INTERROGATOIRE = "INTERROGATOIRE"
    SAISIE = "SAISIE"
    CERTIFICAT_MEDICAL = "CERTIFICAT_MEDICAL"
    TEMOIGNAGE = "TEMOIGNAGE"
    EXPERTISE = "EXPERTISE"
    NOTIFICATION_DROITS = "NOTIFICATION_DROITS"
    AUTRE = "AUTRE"


class Document(IdTimestampMixin, Base):
    __tablename__ = "documents"

    dossier_id: Mapped[UUID] = mapped_column(ForeignKey("dossiers.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    type_piece: Mapped[TypePiece] = mapped_column(Enum(TypePiece, name="type_piece"), default=TypePiece.AUTRE)
    file_key: Mapped[str] = mapped_column(String(500), unique=True)
    file_hash_sha256: Mapped[str] = mapped_column(String(64))
    mime_type: Mapped[str] = mapped_column(String(160))
    size_bytes: Mapped[int]
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(32), default="pending")
    uploaded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dossier: Mapped["Dossier"] = relationship(back_populates="documents")