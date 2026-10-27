"""Load canonical constitutional text and reject unverified references."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pgvector.sqlalchemy import Vector
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.constitutional_article import ConstitutionalArticle as ConstitutionalArticleModel


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "constitution_rdc.json"


class ConstitutionalReferenceError(ValueError):
    """Raised when a reference cannot be verified against the source registry."""


@dataclass(frozen=True)
class ConstitutionalArticle:
    numero: str
    alinea: str | None
    texte: str
    theme: str
    source: str = "Constitution RDC 2006 révisée"


def load_articles(path: Path = DATA_PATH) -> list[ConstitutionalArticle]:
    """Load article text from either the flat schema or the full nested source."""
    with path.open(encoding="utf-8") as source_file:
        source_data: Any = json.load(source_file)

    if isinstance(source_data, list):
        raw_articles = source_data
        source_name = "Constitution RDC 2006 révisée"
    elif isinstance(source_data, dict):
        metadata = source_data.get("metadata", {})
        source_name = (
            metadata.get("journal_officiel", "Constitution RDC 2006 révisée")
            if isinstance(metadata, dict)
            else "Constitution RDC 2006 révisée"
        )
        raw_articles = []

        def collect_articles(value: Any) -> None:
            if isinstance(value, dict):
                if "numero" in value and isinstance(value.get("texte"), str):
                    raw_articles.append(value)
                    return
                for child in value.values():
                    collect_articles(child)
            elif isinstance(value, list):
                for child in value:
                    collect_articles(child)

        collect_articles(source_data.get("titres", []))
    else:
        raise ValueError("Le registre constitutionnel doit être une liste ou un objet JSON.")

    articles: list[ConstitutionalArticle] = []
    for item in raw_articles:
        if not isinstance(item, dict):
            raise ValueError("Chaque article du registre doit être un objet JSON.")
        try:
            article = ConstitutionalArticle(
                numero=str(item["numero"]),
                alinea=None if item.get("alinea") is None else str(item["alinea"]),
                texte=str(item["texte"]).strip(),
                theme=str(item.get("theme", "constitution")),
                source=str(item.get("source", source_name)),
            )
        except KeyError as error:
            raise ValueError(f"Champ obligatoire absent : {error.args[0]}.") from error
        if not article.numero or not article.texte or not article.theme:
            raise ValueError("Les champs numero, texte et theme doivent être renseignés.")
        articles.append(article)
        if article.numero == "17" and article.alinea is None:
            innocence_sentence = re.search(
                r"Toute personne accusée d'une infraction est présumée innocente jusqu'à ce que sa culpabilité ait été établie par un jugement définitif\.",
                article.texte,
            )
            if innocence_sentence:
                articles.append(
                    ConstitutionalArticle(
                        numero="17",
                        alinea="9",
                        texte=innocence_sentence.group(0),
                        theme="presomption_innocence",
                        source=article.source,
                    )
                )
    return articles


def get_article(
    numero: str,
    alinea: str | None = None,
    articles: list[ConstitutionalArticle] | None = None,
) -> ConstitutionalArticle:
    """Return a registered article or fail closed when it is unavailable."""
    available_articles = load_articles() if articles is None else articles
    for article in available_articles:
        if article.numero == numero and article.alinea == alinea:
            return article
    raise ConstitutionalReferenceError(
        f"Article {numero}, alinéa {alinea or 'non précisé'} absent du registre vérifié."
    )


def validate_reference(
    reference: dict[str, Any],
    articles: list[ConstitutionalArticle] | None = None,
) -> ConstitutionalArticle:
    """Resolve a cited article and require the supplied text to match exactly."""
    try:
        article = get_article(
            str(reference["article"]),
            None if reference.get("alinea") is None else str(reference["alinea"]),
            articles,
        )
    except KeyError as error:
        raise ConstitutionalReferenceError(
            f"Champ de référence obligatoire absent : {error.args[0]}."
        ) from error

    if reference.get("texte") != article.texte:
        raise ConstitutionalReferenceError(
            f"Le texte cité pour l'article {article.numero} ne correspond pas au registre."
        )
    return article


async def load_indexed_articles(db: AsyncSession) -> list[ConstitutionalArticleModel]:
    result = await db.scalars(select(ConstitutionalArticleModel).order_by(ConstitutionalArticleModel.numero))
    return list(result)


async def embed_query(text: str) -> list[float]:
    settings = get_settings()
    if not settings.llm_base_url or not settings.llm_api_key:
        raise RuntimeError("Le fournisseur d'embeddings n'est pas configuré.")
    endpoint = f"{settings.llm_base_url.rstrip('/')}/embeddings"
    headers = {"Authorization": f"Bearer {settings.llm_api_key.get_secret_value()}"}
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        response = await client.post(
            endpoint,
            headers=headers,
            json={"model": settings.embedding_model, "input": text},
        )
        response.raise_for_status()
    embedding = response.json()["data"][0]["embedding"]
    if len(embedding) != 1536:
        raise ValueError("Le modèle d'embedding doit produire exactement 1536 dimensions.")
    return embedding


async def search_articles(
    db: AsyncSession, query: str, top_k: int = 5
) -> list[ConstitutionalArticleModel]:
    if not query.strip():
        raise ValueError("La recherche constitutionnelle ne peut pas être vide.")
    embedding = await embed_query(query)
    distance = ConstitutionalArticleModel.embedding.cosine_distance(embedding)
    result = await db.scalars(
        select(ConstitutionalArticleModel)
        .where(ConstitutionalArticleModel.embedding.is_not(None))
        .order_by(distance)
        .limit(max(1, min(top_k, 20)))
    )
    return list(result)


def get_article_text(numero: str, alinea: str | None = None) -> str:
    return get_article(numero, alinea).texte