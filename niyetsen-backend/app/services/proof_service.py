"""
Niyetsen — Kanıt Doğrulama Servisi (MASTER_PLAN §1.5)
Foto + görev başlığı → Gemini Vision → 0-100 güven skoru.
  skor >= 60            → onay
  skor <  60, deneme <3 → nazik "bir kare daha" (reddetme, davet et)
  3. deneme             → kullanıcı beyanıyla KABUL (kullanıcıyla savaşma —
                          philosophy.py Yasa 1: sistem polislik için değil,
                          alışkanlık için var)
Konum verilmişse skora +10 bonus güven.
"""
from __future__ import annotations

from app.config import settings
from app.core import prompts
from app.core.gemini_client import GeminiUnavailable, generate_json_with_image
from app.models.schemas import ProofResult

ALLOWED_MIME = {"image/jpeg", "image/png"}
FILE_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}


class ProofRejected(ValueError):
    """Dosya kurallara uymuyor (boyut/tip) — 400 döner."""


def sniff_image_mime(image_bytes: bytes) -> str | None:
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


def resolve_mime_type(image_bytes: bytes, declared_mime: str) -> str:
    normalized = (declared_mime or "").split(";")[0].strip().lower()
    if normalized in ALLOWED_MIME:
        return normalized
    sniffed = sniff_image_mime(image_bytes)
    if sniffed:
        return sniffed
    raise ProofRejected("Sadece JPEG veya PNG kabul edilir.")


def validate_upload(image_bytes: bytes, mime_type: str) -> str:
    resolved = resolve_mime_type(image_bytes, mime_type)
    if len(image_bytes) > settings.PROOF_MAX_BYTES:
        raise ProofRejected("Fotoğraf 5 MB'den büyük olamaz.")
    if len(image_bytes) < 100:
        raise ProofRejected("Fotoğraf okunamadı.")
    if not any(image_bytes.startswith(signature) for signature in FILE_SIGNATURES[resolved]):
        raise ProofRejected("Dosya içeriği bildirilen JPEG/PNG türüyle eşleşmiyor.")
    return resolved


async def evaluate_proof(
    task_title: str,
    image_bytes: bytes,
    mime_type: str,
    attempt_no: int,
    has_location: bool = False,
    *,
    tiny_version: str = "",
    categories: list[str] | None = None,
    task_type: str = "alışkanlık",
) -> ProofResult:
    resolved_mime = validate_upload(image_bytes, mime_type)

    # 3. deneme: beyanla kabul — Vision'a hiç gitmeden onayla, maliyet de tasarruf.
    if attempt_no >= settings.PROOF_MAX_ATTEMPTS:
        return ProofResult(
            approved=True, confidence=settings.PROOF_MIN_CONFIDENCE,
            reason="Sana güveniyorum — beyanınla kabul edildi. 🌙",
            attempt_no=attempt_no, accepted_by_declaration=True,
        )

    try:
        data = await generate_json_with_image(
            prompt=prompts.PROOF_VALIDATION_PROMPT.format(
                task_title=task_title,
                tiny_version=tiny_version or "belirtilmedi",
                categories=", ".join(categories or []) or "belirtilmedi",
                task_type=task_type,
            ),
            image_bytes=image_bytes,
            mime_type=resolved_mime,
        )
    except GeminiUnavailable as exc:
        msg = str(exc).casefold()
        if "invalid_argument" in msg and (
            "image" in msg or "process input" in msg or "unable to process" in msg
        ):
            raise ProofRejected(
                "Fotoğraf okunamadı veya işlenemedi. Yeni bir kare çekip tekrar dener misin?"
            ) from exc
        raise

    try:
        confidence = max(0, min(100, int(data.get("confidence") or 0)))
    except (TypeError, ValueError):
        confidence = 0
    if has_location:
        confidence = min(100, confidence + 10)

    approved = confidence >= settings.PROOF_MIN_CONFIDENCE
    reason = str(data.get("reason") or "")
    if not approved:
        reason = "Tam emin olamadım, bir kare daha dener misin? " + reason

    return ProofResult(
        approved=approved, confidence=confidence,
        reason=reason, attempt_no=attempt_no,
    )
