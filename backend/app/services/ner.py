import re


DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b")
PV_PATTERN = re.compile(r"\b(?:PV|P\.V\.)\s*(?:n[°o]\s*)?[A-Z0-9/-]+", re.IGNORECASE)
ARTICLE_PATTERN = re.compile(r"\barticle\s+(\d+)(?:\s+(?:alinéa|al\.)\s*(\d+))?", re.IGNORECASE)


def extract_entities(text: str) -> dict[str, list[str]]:
    dates = list(dict.fromkeys(DATE_PATTERN.findall(text)))
    return {"persons": [], "dates": dates, "locations": [], "organizations": []}


def extract_legal_entities(text: str) -> dict[str, list[str]]:
    return {
        "infractions": [],
        "articles": [match.group(0) for match in ARTICLE_PATTERN.finditer(text)],
        "numero_pv": [match.group(0) for match in PV_PATTERN.finditer(text)],
    }


def extract_dates_custody(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"garde\s+à\s+vue\s+du\s+([^\n;]+?)\s+au\s+([^\n;.]+)", re.IGNORECASE
    )
    return [(match.group(1).strip(), match.group(2).strip()) for match in pattern.finditer(text)]