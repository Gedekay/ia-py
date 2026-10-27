from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdTimestampMixin

if TYPE_CHECKING:
    from app.models.analyse import Analyse
    from app.models.document import Document
    from app.models.user import User


class StatutDossier(StrEnum):
    OUVERT = "OUVERT"
    EN_ANALYSE = "EN_ANALYSE"
    CLOS = "CLOS"


class Dossier(IdTimestampMixin, Base):
    __tablename__ = "dossiers"

    numero_dossier: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    date_ouverture: Mapped[date] = mapped_column(Date)
    infraction_type: Mapped[str] = mapped_column(String(160))
    statut: Mapped[StatutDossier] = mapped_column(Enum(StatutDossier, name="statut_dossier"), default=StatutDossier.OUVERT)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

    created_by: Mapped["User"] = relationship(back_populates="dossiers_created")
    documents: Mapped[list["Document"]] = relationship(back_populates="dossier", cascade="all, delete-orphan")
    analyses: Mapped[list["Analyse"]] = relationship(back_populates="dossier", cascade="all, delete-orphan")