import json
import re
from typing import Any

import httpx

from app.core.config import get_settings


SYSTEM_PROMPT = """Tu es un assistant de conformité procédurale. Tu ne rends aucun jugement et ne conclus jamais à la culpabilité d'une personne. Distingue les faits documentés, les informations absentes et les vérifications à effectuer. N'invente aucun article ni texte de loi. Les seules références autorisées sont celles fournies dans le contexte, à reprendre textuellement. Si le contexte ne permet pas une conclusion, indique que la vérification humaine est nécessaire. Réponds uniquement en JSON conforme au schéma demandé."""


def build_prompt(
    dossier: dict[str, Any],
    documents: list[dict[str, Any]],
    entities: dict[str, Any],
    top_articles: list[dict[str, str]],
) -> list[dict[str, str]]:
    context = {
        "dossier": dossier,
        "documents": documents,
        "entites_extraites": entities,
        "references_constitutionnelles_verifiees": top_articles,
        "schema": {
            "statut_global": "string descriptive, jamais une appréciation de culpabilité",
            "synthese": "object",
            "controles_procedure": "array; chaque élément cite une référence fournie",
            "elements_a_charge": "array vide si aucun élément vérifiable; chaque élément cite une référence fournie",
            "pistes_a_explorer": "array; chaque élément cite une référence fournie",
            "recommandation_finale": "string neutre, limitée aux vérifications procédurales",
        },
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
    ]


async def call_llm(messages: list[dict[str, str]], model: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    if settings.llm_provider not in {"openai_compatible", "openai", "mistral", "vllm"}:
        raise RuntimeError("Aucun fournisseur LLM compatible n'est configuré.")
    if not settings.llm_base_url or not settings.llm_api_key or not (model or settings.llm_model):
        raise RuntimeError("LLM_BASE_URL, LLM_API_KEY et LLM_MODEL sont requis.")
    endpoint = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key.get_secret_value()}"}
    payload = {"model": model or settings.llm_model, "messages": messages, "response_format": {"type": "json_object"}}
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        response = await client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
    body = response.json()
    return parse_json_response(body["choices"][0]["message"]["content"])


def parse_json_response(raw: str) -> dict[str, Any]:
    candidate = raw.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.IGNORECASE)
    start = candidate.find("{")
    if start < 0:
        raise ValueError("La réponse du modèle ne contient pas d'objet JSON.")
    try:
        value, end = json.JSONDecoder().raw_decode(candidate[start:])
    except json.JSONDecodeError as error:
        raise ValueError("La réponse du modèle contient un JSON invalide.") from error
    if candidate[start + end :].strip():
        raise ValueError("La réponse du modèle contient du texte après l'objet JSON.")
    if not isinstance(value, dict):
        raise ValueError("La réponse du modèle doit être un objet JSON.")
    return value


def assert_no_culpability_word(text: str) -> None:
    prohibited = re.compile(r"\bcoupable\b|\bauteur\s+des\s+faits\b|\bresponsable\s+de\b", re.IGNORECASE)
    if prohibited.search(text):
        raise ValueError("La sortie contient une formulation accusatoire interdite.")


def retry_with_feedback(raw: str, error: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Corrige cette sortie pour qu'elle respecte le schéma JSON et les références fournies. "
                "Ne crée aucune référence. Erreur de validation : "
                f"{error}\nSortie précédente :\n{raw}"
            ),
        },
    ]