from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.models.document import Document, TypePiece
from app.schemas.analyse import ControleProcedure, GraviteEnum, ReferenceConstitutionnelle
from app.services.constitutional import ConstitutionalArticle


class ConstitutionalSourceUnavailable(RuntimeError):
    """A procedural rule cannot be reported without its verified legal source."""


def _reference(articles: list[ConstitutionalArticle], numero: str) -> ReferenceConstitutionnelle:
    article = next((item for item in articles if item.numero == numero), None)
    if article is None:
        raise ConstitutionalSourceUnavailable(
            f"Article {numero} absent du registre officiel ; contrôle suspendu."
        )
    return ReferenceConstitutionnelle(
        article=article.numero,
        alinea=article.alinea,
        texte=article.texte,
        source="Constitution RDC 2006 révisée",
    )


def check_garde_a_vue(
    documents: list[Document], articles: list[ConstitutionalArticle]
) -> ControleProcedure | None:
    limit_hours = get_settings().max_garde_a_vue_hours
    for document in documents:
        text = document.extracted_text or ""
        start = _parse_datetime(text, r"garde\s+à\s+vue\s+du\s+([^\n;]+?)\s+au\s+([^\n;.]+)")
        if start is None:
            continue
        began, ended = start
        duration_hours = (ended - began).total_seconds() / 3600
        if duration_hours > limit_hours:
            return ControleProcedure(
                code="GARDE_A_VUE_DEPASSEE",
                gravite=GraviteEnum.CRITIQUE,
                description=f"La durée documentée de garde à vue est de {duration_hours:g} heures.",
                consequence="Une vérification juridique de la régularité de la procédure est nécessaire.",
                references_constitutionnelles=[_reference(articles, "18")],
            )
    return None


def _parse_datetime(text: str, pattern: str) -> tuple[datetime, datetime] | None:
    import re

    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    formats = ("%d/%m/%Y à %Hh%M", "%d/%m/%Y %H:%M", "%d/%m/%Y à %H:%M")
    for date_format in formats:
        try:
            return datetime.strptime(match.group(1).strip(), date_format), datetime.strptime(
                match.group(2).strip(), date_format
            )
        except ValueError:
            continue
    return None


def check_notification_droits(
    documents: list[Document], articles: list[ConstitutionalArticle]
) -> ControleProcedure | None:
    if any(document.type_piece == TypePiece.NOTIFICATION_DROITS for document in documents):
        return None
    return ControleProcedure(
        code="NOTIFICATION_DROITS_NON_DOCUMENTEE",
        gravite=GraviteEnum.MAJEURE,
        description="Aucune pièce classée comme notification des droits n'est présente au dossier.",
        consequence="Vérifier si la notification a eu lieu et joindre sa pièce justificative.",
        references_constitutionnelles=[_reference(articles, numero) for numero in ("18", "19")],
    )


def check_avocat_presence(
    documents: list[Document], articles: list[ConstitutionalArticle]
) -> ControleProcedure | None:
    combined_text = " ".join(document.extracted_text or "" for document in documents).casefold()
    if "avocat" in combined_text:
        return None
    return ControleProcedure(
        code="ASSISTANCE_AVOCAT_NON_DOCUMENTEE",
        gravite=GraviteEnum.INFO,
        description="Les documents traités ne mentionnent pas l'assistance d'un avocat.",
        consequence="Vérifier la situation avec les pièces originales et les personnes concernées.",
        references_constitutionnelles=[_reference(articles, "19")],
    )


def check_pieces_obligatoires(
    infraction_type: str, documents: list[Document], articles: list[ConstitutionalArticle]
) -> list[ControleProcedure]:
    required = CHECKLISTS.get(infraction_type.casefold(), ())
    present = {document.type_piece for document in documents}
    missing = [piece for piece in required if piece not in present]
    if not missing:
        return []
    labels = ", ".join(piece.value for piece in missing)
    return [
        ControleProcedure(
            code="PIECES_OBLIGATOIRES_MANQUANTES",
            gravite=GraviteEnum.MAJEURE,
            description=f"Pièces à vérifier ou compléter : {labels}.",
            consequence="Confirmer la liste applicable selon les faits et les règles de procédure en vigueur.",
            references_constitutionnelles=[_reference(articles, "19")],
        )
    ]


def check_delais_instruction(
    dossier: Any, articles: list[ConstitutionalArticle]
) -> ControleProcedure | None:
    elapsed_days = (datetime.now().date() - dossier.date_ouverture).days
    if elapsed_days <= 365:
        return None
    return ControleProcedure(
        code="DELAI_INSTRUCTION_A_VERIFIER",
        gravite=GraviteEnum.INFO,
        description=f"Le dossier est ouvert depuis {elapsed_days} jours.",
        consequence="Un professionnel doit apprécier le caractère raisonnable du délai au regard du dossier.",
        references_constitutionnelles=[_reference(articles, "19")],
    )


CHECKLISTS: dict[str, tuple[TypePiece, ...]] = {
    "vol qualifié": (TypePiece.PROCES_VERBAL, TypePiece.SAISIE),
    "vol": (TypePiece.PROCES_VERBAL,),
    "assassinat": (TypePiece.PROCES_VERBAL, TypePiece.EXPERTISE),
    "viol": (TypePiece.PROCES_VERBAL, TypePiece.CERTIFICAT_MEDICAL),
}

Rule = Callable[..., Any]
REGISTRY: list[Rule] = [
    check_garde_a_vue,
    check_notification_droits,
    check_avocat_presence,
]