from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.analyse import StatutAnalyse


class GraviteEnum(StrEnum):
    INFO = "INFO"
    MAJEURE = "MAJEURE"
    CRITIQUE = "CRITIQUE"


class ForceEnum(StrEnum):
    INDICE_MATERIEL = "INDICE_MATERIEL"
    TEMOIGNAGE = "TEMOIGNAGE"
    AVEU = "AVEU"


class ReferenceConstitutionnelle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article: str
    alinea: str | None = None
    texte: str
    source: str

    @field_validator("texte", "source")
    @classmethod
    def non_vide(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La référence et sa source doivent être renseignées.")
        return value


class ControleProcedure(BaseModel):
    code: str
    gravite: GraviteEnum
    description: str
    consequence: str | None = None
    references_constitutionnelles: list[ReferenceConstitutionnelle] = Field(min_length=1)


class ElementACharge(BaseModel):
    description: str
    source_document: str | None = None
    force: ForceEnum
    reference_legale: ReferenceConstitutionnelle


class PisteAExplorer(BaseModel):
    piste: str
    justification: str
    references_constitutionnelles: list[ReferenceConstitutionnelle] = Field(min_length=1)


class AnalyseResultat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statut_global: str
    avertissement_legal: str = "Outil d'aide. La présomption d'innocence prévaut (Art. 17 al. 9, Constitution RDC)."
    synthese: dict[str, int | str]
    controles_procedure: list[ControleProcedure]
    elements_a_charge: list[ElementACharge]
    pistes_a_explorer: list[PisteAExplorer]
    recommandation_finale: str


class AnalyseCreateResponse(BaseModel):
    analyse_id: UUID
    statut: StatutAnalyse


class AnalyseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dossier_id: UUID
    statut: StatutAnalyse
    resultat: AnalyseResultat | None
    error_message: str | None
    created_at: datetime
    finished_at: datetime | None