import json
import tempfile
import unittest
from pathlib import Path

from app.services.constitutional import (
    DATA_PATH,
    ConstitutionalArticle,
    ConstitutionalReferenceError,
    get_article,
    load_articles,
    validate_reference,
)


class ConstitutionalRegistryTests(unittest.TestCase):
    def test_loads_full_nested_constitution_source(self) -> None:
        articles = load_articles(DATA_PATH)

        self.assertGreaterEqual(len(articles), 229)
        innocence = get_article("17", "9", articles)
        self.assertEqual(
            innocence.texte,
            "Toute personne accusée d'une infraction est présumée innocente jusqu'à ce que sa culpabilité ait été établie par un jugement définitif.",
        )

    def test_empty_registry_does_not_invent_article_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "constitution_rdc.json"
            path.write_text("[]", encoding="utf-8")

            self.assertEqual(load_articles(path), [])
            with self.assertRaises(ConstitutionalReferenceError):
                get_article("18", articles=[])

    def test_reference_must_match_canonical_text_exactly(self) -> None:
        articles = [
            ConstitutionalArticle(
                numero="18", alinea=None, texte="Texte source vérifié.", theme="test"
            )
        ]

        canonical = validate_reference(
            {"article": "18", "texte": "Texte source vérifié."}, articles
        )
        self.assertEqual(canonical.texte, "Texte source vérifié.")

        with self.assertRaises(ConstitutionalReferenceError):
            validate_reference({"article": "18", "texte": "Texte inventé."}, articles)

    def test_registry_rejects_malformed_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "constitution_rdc.json"
            path.write_text(json.dumps([{"numero": "18"}]), encoding="utf-8")

            with self.assertRaises(ValueError):
                load_articles(path)


if __name__ == "__main__":
    unittest.main()