from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdTimestampMixin

if TYPE_CHECKING:
    from app.models.dossier import Dossier


class StatutAnalyse(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"


class Analyse(IdTimestampMixin, Base):
    __tablename__ = "analyses"

    dossier_id: Mapped[UUID] = mapped_column(ForeignKey("dossiers.id", ondelete="CASCADE"), index=True)
    statut: Mapped[StatutAnalyse] = mapped_column(Enum(StatutAnalyse, name="statut_analyse"), default=StatutAnalyse.PENDING)
    resultat: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    llm_tokens_used: Mapped[int | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dossier: Mapped["Dossier"] = relationship(back_populates="analyses")