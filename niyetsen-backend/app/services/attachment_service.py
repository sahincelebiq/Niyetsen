"""Sohbet ekleri — PDF/DOCX metin çıkarımı, PNG/JPEG için kısa görsel özeti."""
from __future__ import annotations

import io
import logging

from app.core.gemini_client import generate_json_with_image

log = logging.getLogger("niyetsen.attachment")

MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
ALLOWED_MIME = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class AttachmentRejected(ValueError):
    """Geçersiz veya desteklenmeyen ek."""


def validate_attachment(data: bytes, mime_type: str) -> None:
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise AttachmentRejected("Dosya en fazla 5 MB olabilir.")
    normalized = (mime_type or "").split(";")[0].strip().lower()
    if normalized not in ALLOWED_MIME:
        raise AttachmentRejected("Yalnızca PDF, PNG, JPEG ve DOCX desteklenir.")


def _extract_pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    chunks: list[str] = []
    for page in reader.pages[:12]:
        text = (page.extract_text() or "").strip()
        if text:
            chunks.append(text)
    return "\n".join(chunks)[:6000]


def _extract_docx_text(data: bytes) -> str:
    from docx import Document

    document = Document(io.BytesIO(data))
    lines = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    return "\n".join(lines)[:6000]


async def _summarize_image(data: bytes, mime_type: str, filename: str) -> str:
    # faz8.13: şema artık çağrı bazlı — ek özeti kendi şemasını geçirir
    # (önceden kanıt şemasına sabitti → summary hep boş dönebiliyordu).
    result = await generate_json_with_image(
        prompt=(
            f'Bu görsel sohbet eki ({filename}). Kullanıcının niyet planına yardımcı olacak '
            "kısa Türkçe özet çıkar. SADECE JSON: "
            '{"summary":"<en fazla 4 cümle Türkçe>"}'
        ),
        image_bytes=data,
        mime_type=mime_type,
        response_schema={
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        },
    )
    return str(result.get("summary") or "Görsel eklendi.")


async def ingest_attachment(data: bytes, mime_type: str, filename: str) -> str:
    validate_attachment(data, mime_type)
    normalized = mime_type.split(";")[0].strip().lower()
    safe_name = filename or "ek"

    if normalized.startswith("image/"):
        return await _summarize_image(data, normalized, safe_name)

    if normalized == "application/pdf":
        text = _extract_pdf_text(data)
        if not text:
            raise AttachmentRejected("PDF'den metin okunamadı.")
        return text

    text = _extract_docx_text(data)
    if not text:
        raise AttachmentRejected("DOCX dosyasından metin okunamadı.")
    return text
