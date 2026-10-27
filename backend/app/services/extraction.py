import io
import re
import unicodedata

import pymupdf as fitz
import pytesseract
from docx import Document as DocxDocument
from PIL import Image


SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/jpeg",
    "image/png",
    "image/tiff",
}


def clean_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    normalized = re.sub(r"[\t\f\v ]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _extract_pdf(data: bytes) -> str:
    with fitz.open(stream=data, filetype="pdf") as pdf:
        extracted_pages = []
        for page in pdf:
            page_text = page.get_text()
            if not page_text.strip():
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                page_text = pytesseract.image_to_string(image, lang="fra")
            extracted_pages.append(page_text)
        return clean_text("\n".join(extracted_pages))


def _extract_docx(data: bytes) -> str:
    document = DocxDocument(io.BytesIO(data))
    return clean_text("\n".join(paragraph.text for paragraph in document.paragraphs))


def _extract_image_ocr(data: bytes) -> str:
    image = Image.open(io.BytesIO(data))
    return clean_text(pytesseract.image_to_string(image, lang="fra"))


def detect_language(text: str) -> str:
    return "fr" if text.strip() else "unknown"


def extract_text(file_bytes: bytes, mime: str) -> str:
    if not file_bytes:
        raise ValueError("Le fichier est vide.")
    if mime == "application/pdf":
        result = _extract_pdf(file_bytes)
    elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        result = _extract_docx(file_bytes)
    elif mime == "text/plain":
        result = clean_text(file_bytes.decode("utf-8-sig"))
    elif mime in {"image/jpeg", "image/png", "image/tiff"}:
        result = _extract_image_ocr(file_bytes)
    else:
        raise ValueError(f"Type de fichier non pris en charge : {mime}.")
    return result