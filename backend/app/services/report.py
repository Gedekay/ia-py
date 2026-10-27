import hashlib
import io
import json
from datetime import UTC, datetime
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas

from app.schemas.analyse import AnalyseResultat


def generate_json_export(analyse: AnalyseResultat, user_email: str) -> dict[str, Any]:
    report_data = analyse.model_dump(mode="json")
    canonical_report = json.dumps(report_data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_by": user_email,
        "resultat": report_data,
        "hash_sha256": hashlib.sha256(canonical_report.encode("utf-8")).hexdigest(),
    }
    return payload


def generate_pdf(analyse: AnalyseResultat, user_email: str) -> bytes:
    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4, pageCompression=0)
    width, height = A4
    json_payload = generate_json_export(analyse, user_email)
    report_hash = str(json_payload["hash_sha256"])
    y = height - 48
    pdf.setTitle("Rapport d'analyse SAAJD")
    pdf.setFillColorRGB(0.55, 0.08, 0.08)
    pdf.drawString(40, y, "OUTIL D'AIDE - PRESOMPTION D'INNOCENCE")
    pdf.setFillColorRGB(0, 0, 0)
    y -= 28
    for text in [
        analyse.avertissement_legal,
        f"Statut : {analyse.statut_global}",
        analyse.recommandation_finale,
        f"Hash SHA-256 du rapport structuré : {report_hash}",
    ]:
        for line in _wrap(text, 95):
            if y < 55:
                pdf.showPage()
                y = height - 48
            pdf.drawString(40, y, line)
            y -= 15
    qr_code = qr.QrCodeWidget(report_hash)
    bounds = qr_code.getBounds()
    size = 72
    drawing = Drawing(size, size, transform=[size / (bounds[2] - bounds[0]), 0, 0, size / (bounds[3] - bounds[1]), 0, 0])
    drawing.add(qr_code)
    if y < 120:
        pdf.showPage()
        y = height - 48
    renderPDF.draw(drawing, pdf, width - 112, max(y - 80, 55))
    pdf.saveState()
    pdf.setFillColorRGB(0.65, 0.65, 0.65)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(40, 25, f"Généré par {user_email} le {datetime.now(UTC).isoformat()}")
    pdf.restoreState()
    pdf.save()
    return output.getvalue()


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines