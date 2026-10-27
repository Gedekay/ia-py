from datetime import date
from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.dossier import StatutDossier
from app.schemas.common import ORMModel


class DossierCreate(ORMModel):
    numero_dossier: str = Field(min_length=1, max_length=100)
    date_ouverture: date = Field(default_factory=date.today)
    infraction_type: str = Field(min_length=1, max_length=160)
    metadata_: dict[str, Any] = Field(default_factory=dict)


class DossierUpdate(ORMModel):
    infraction_type: str | None = Field(default=None, min_length=1, max_length=160)
    statut: StatutDossier | None = None
    metadata_: dict[str, Any] | None = None


class DossierRead(ORMModel):
    id: UUID
    numero_dossier: str
    date_ouverture: date
    infraction_type: str
    statut: StatutDossier
    metadata_: dict[str, Any]
    created_by_id: UUID


class DossierList(ORMModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    statut: StatutDossier | None = None
    infraction_type: str | None = None