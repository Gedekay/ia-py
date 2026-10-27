import re
from collections.abc import Iterable
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import ConstitutionalRefMissingError
from app.schemas.analyse import AnalyseResultat, ReferenceConstitutionnelle
from app.services.constitutional import (
    ConstitutionalArticle,
    ConstitutionalReferenceError,
    validate_reference,
)


LEGAL_DISCLAIMER_PREFIX = (
    "Ce rapport est un outil d'aide. Il ne constitue ni une mise en cause ni un jugement. "
    "La présomption d'innocence prévaut. Art. 17 al. 9 — "
)
PROHIBITED_PATTERNS = (
    re.compile(r"\bcoupable\b", re.IGNORECASE),
    re.compile(r"\bauteur\s+des\s+faits\b", re.IGNORECASE),
    re.compile(r"\bresponsable\s+de\b", re.IGNORECASE),
)


def _reference_dict(reference: ReferenceConstitutionnelle) -> dict[str, Any]:
    return reference.model_dump()


def _references(result: AnalyseResultat) -> Iterable[ReferenceConstitutionnelle]:
    for control in result.controles_procedure:
        yield from control.references_constitutionnelles
    for element in result.elements_a_charge:
        yield element.reference_legale
    for lead in result.pistes_a_explorer:
        yield from lead.references_constitutionnelles


def ensure_no_culpability_language(result: AnalyseResultat) -> None:
    for value in result.model_dump().values():
        if isinstance(value, str) and any(pattern.search(value) for pattern in PROHIBITED_PATTERNS):
            raise ValueError("Le rapport contient une formulation accusatoire interdite.")
        if isinstance(value, (dict, list)):
            _scan_nested_text(value)


def _scan_nested_text(value: Any) -> None:
    if isinstance(value, str) and any(pattern.search(value) for pattern in PROHIBITED_PATTERNS):
        raise ValueError("Le rapport contient une formulation accusatoire interdite.")
    if isinstance(value, dict):
        for nested in value.values():
            _scan_nested_text(nested)
    if isinstance(value, list):
        for nested in value:
            _scan_nested_text(nested)


def ensure_articles_exist(
    result: AnalyseResultat,
    articles: list[ConstitutionalArticle],
) -> None:
    for reference in _references(result):
        try:
            canonical = validate_reference(_reference_dict(reference), articles)
        except ConstitutionalReferenceError as error:
            raise ConstitutionalRefMissingError(str(error)) from error
        reference.texte = canonical.texte
        reference.source = canonical.source


def ensure_legal_disclaimer(
    result: AnalyseResultat,
    articles: list[ConstitutionalArticle],
) -> None:
    try:
        canonical = next(
            article for article in articles if article.numero == "17" and article.alinea == "9"
        )
    except StopIteration as error:
        raise ConstitutionalRefMissingError(
            "Analyse refusée : le texte vérifié de l'article 17, alinéa 9, est absent du registre."
        ) from error
    result.avertissement_legal = f"{LEGAL_DISCLAIMER_PREFIX}{canonical.texte} ({canonical.source})."


def validate_analyse_resultat(
    data: dict[str, Any],
    articles: list[ConstitutionalArticle],
) -> AnalyseResultat:
    try:
        result = AnalyseResultat.model_validate(data)
    except ValidationError as error:
        raise ConstitutionalRefMissingError(
            "La sortie d'analyse ne respecte pas le schéma validé."
        ) from error
    ensure_articles_exist(result, articles)
    ensure_no_culpability_language(result)
    ensure_legal_disclaimer(result, articles)
    return result