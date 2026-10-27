import unittest
import io
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.document import TypePiece
from app.schemas.analyse import AnalyseResultat
from app.services.classifier import classify_piece
from app.services.constitutional import ConstitutionalArticle
from app.services.extraction import _extract_pdf
from app.services.llm_engine import parse_json_response
from app.services.report import generate_pdf, generate_json_export
from app.core.exceptions import ConstitutionalRefMissingError
from app.services.validator import validate_analyse_resultat
from app.main import app


class ServiceTests(unittest.TestCase):
    def test_health_endpoint_reports_unavailable_dependencies(self) -> None:
        with (
            patch("app.main.async_session_maker") as session_factory,
            patch("redis.asyncio.Redis.from_url", side_effect=RuntimeError("Redis down")),
            patch("app.main.get_minio_client", side_effect=RuntimeError("MinIO down")),
        ):
            session_factory.return_value.__aenter__.return_value.execute.side_effect = RuntimeError("DB down")
            response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "degraded")
        self.assertEqual(set(response.json()["services"]), {"database", "redis", "minio"})

    def test_api_routes_are_versioned(self) -> None:
        paths = app.openapi()["paths"]
        self.assertIn("/api/v1/dossiers", paths)
        self.assertIn("/api/v1/auth/login", paths)
        self.assertIn("/api/v1/analyses/{analyse_id}/report.pdf", paths)

    def test_scanned_pdf_uses_ocr_fallback(self) -> None:
        import pymupdf

        output = io.BytesIO()
        with pymupdf.open() as pdf:
            pdf.new_page()
            pdf.save(output)
        with patch("app.services.extraction.pytesseract.image_to_string", return_value="Texte OCR") as ocr:
            self.assertEqual(_extract_pdf(output.getvalue()), "Texte OCR")
            ocr.assert_called_once()

    def test_pdf_export_contains_integrity_hash_and_disclaimer(self) -> None:
        import pymupdf

        result = AnalyseResultat(
            statut_global="A_VERIFIER",
            synthese={},
            controles_procedure=[],
            elements_a_charge=[],
            pistes_a_explorer=[],
            recommandation_finale="Vérification humaine nécessaire.",
            avertissement_legal="Bandeau légal de test.",
        )
        exported = generate_json_export(result, "agent@example.org")
        pdf = generate_pdf(result, "agent@example.org")
        with pymupdf.open(stream=pdf, filetype="pdf") as generated_pdf:
            text = " ".join(page.get_text() for page in generated_pdf)

        self.assertIn(str(exported["hash_sha256"]), text)
        self.assertIn("Bandeau légal de test", text)

    def test_classifier_detects_notification(self) -> None:
        self.assertEqual(classify_piece("Procès-verbal de notification des droits"), TypePiece.NOTIFICATION_DROITS)

    def test_parse_json_response_accepts_json_fence(self) -> None:
        self.assertEqual(parse_json_response('```json\n{"ok": true}\n```'), {"ok": True})

    def test_parse_json_response_rejects_trailing_text(self) -> None:
        with self.assertRaises(ValueError):
            parse_json_response('{"ok": true} commentaire')

    def test_analyse_requires_real_exact_constitutional_citations(self) -> None:
        data = {
            "statut_global": "A_VERIFIER",
            "synthese": {},
            "controles_procedure": [
                {
                    "code": "TEST",
                    "gravite": "INFO",
                    "description": "Point à vérifier.",
                    "references_constitutionnelles": [
                        {"article": "18", "texte": "Texte inventé.", "source": "source"}
                    ],
                }
            ],
            "elements_a_charge": [],
            "pistes_a_explorer": [],
            "recommandation_finale": "Vérification humaine nécessaire.",
        }
        article = ConstitutionalArticle("18", None, "Texte officiel vérifié.", "test")

        with self.assertRaises(Exception):
            validate_analyse_resultat(data, [article])

    def test_analyse_rejects_accusatory_language_in_nested_fields(self) -> None:
        data = {
            "statut_global": "A_VERIFIER",
            "synthese": {},
            "controles_procedure": [],
            "elements_a_charge": [],
            "pistes_a_explorer": [],
            "recommandation_finale": "La personne est coupable.",
        }
        with self.assertRaises(ValueError):
            validate_analyse_resultat(data, [])

    def test_analysis_requires_verified_innocence_disclaimer_source(self) -> None:
        data = {
            "statut_global": "A_VERIFIER",
            "synthese": {},
            "controles_procedure": [],
            "elements_a_charge": [],
            "pistes_a_explorer": [],
            "recommandation_finale": "Vérification humaine nécessaire.",
        }
        article_17 = ConstitutionalArticle(
            "17", "9", "Texte officiel de présomption d'innocence.", "Source officielle vérifiée"
        )

        with self.assertRaises(ConstitutionalRefMissingError):
            validate_analyse_resultat(data, [])

        result = validate_analyse_resultat(data, [article_17])
        self.assertIn(article_17.texte, result.avertissement_legal)
        self.assertIn(article_17.source, result.avertissement_legal)


if __name__ == "__main__":
    unittest.main()