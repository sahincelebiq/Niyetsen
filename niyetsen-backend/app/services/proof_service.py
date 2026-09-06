"""
Niyetsen — Kanıt Doğrulama Servisi (MASTER_PLAN §1.5)
Foto + görev başlığı → Gemini Vision → 0-100 güven skoru.
  skor >= 60            → onay (accepted_by_declaration=False, tam +50)
  skor <  60, deneme <3 → nazik "bir kare daha" (reddetme, davet et)
  skor <  60, 3. deneme → beyanla KABUL (kullanıcıyla savaşma) ama Vision
                          ATLANMAZ; gerçek skor korunur, oyun etkisi düşük
                          (POINTS_PER_DECLARATION). H-02.
Vision geçici hata: GeminiUnavailable yükseltilir — 503, deneme yakılmaz,
beyan yolu AÇILMAZ (kota/hata ile +puan bypass yok).
Konum verilmişse skora +10 bonus güven.
"""
from __future__ import annotations

import hashlib

from app.config import settings
from app.core import prompts
from app.core.gemini_client import (
    GeminiUnavailable, PROOF_RESPONSE_SCHEMA, generate_json_with_image,
)
from app.models.schemas import ProofResult

ALLOWED_MIME = {"image/jpeg", "image/png"}
FILE_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}


class ProofRejected(ValueError):
    """Dosya kurallara uymuyor (boyut/tip) — 400 döner."""


def _strip_jpeg_exif(image_bytes: bytes) -> bytes:
    """JPEG APP1 (EXIF/GPS) ve yorum segmentlerini at. Parse bozulursa orijinali koru."""
    if len(image_bytes) < 4 or image_bytes[:2] != b"\xff\xd8":
        return image_bytes
    out = bytearray(b"\xff\xd8")
    i = 2
    try:
        while i + 1 < len(image_bytes):
            if image_bytes[i] != 0xFF:
                out.extend(image_bytes[i:])
                break
            marker = image_bytes[i + 1]
            if marker == 0xDA:  # SOS — görüntü verisi başlar
                out.extend(image_bytes[i:])
                break
            if marker in (0xD8, 0xD9) or (0xD0 <= marker <= 0xD7):
                i += 2
                continue
            if i + 3 >= len(image_bytes):
                out.extend(image_bytes[i:])
                break
            length = int.from_bytes(image_bytes[i + 2 : i + 4], "big")
            segment_end = i + 2 + length
            if segment_end > len(image_bytes) or length < 2:
                out.extend(image_bytes[i:])
                break
            # APP1 EXIF, APP13 IPTC, COM — konum/cihaz sızmasın
            if marker in (0xE1, 0xED, 0xFE):
                i = segment_end
                continue
            out.extend(image_bytes[i:segment_end])
            i = segment_end
        stripped = bytes(out)
        return stripped if len(stripped) >= 100 else image_bytes
    except Exception:  # noqa: BLE001 — strip başarısızsa yüklemeyi düşürme
        return image_bytes


def validate_upload(image_bytes: bytes, mime_type: str) -> None:
    if mime_type not in ALLOWED_MIME:
        raise ProofRejected("Sadece JPEG veya PNG kabul edilir.")
    if len(image_bytes) > settings.PROOF_MAX_BYTES:
        raise ProofRejected("Fotoğraf 5 MB'den büyük olamaz.")
    if len(image_bytes) < 100:
        raise ProofRejected("Fotoğraf okunamadı.")
    if not any(image_bytes.startswith(signature) for signature in FILE_SIGNATURES[mime_type]):
        raise ProofRejected("Dosya içeriği bildirilen JPEG/PNG türüyle eşleşmiyor.")


def prepare_upload(image_bytes: bytes, mime_type: str) -> bytes:
    """Tip/boyut doğrula, JPEG EXIF/GPS'i düş, Vision ve Storage'a temiz bayt ver."""
    validate_upload(image_bytes, mime_type)
    if mime_type == "image/jpeg":
        return _strip_jpeg_exif(image_bytes)
    return image_bytes


def image_content_hash(image_bytes: bytes) -> str:
    """Hazırlanmış kanıt baytlarının sha256'sı — aynı kare tekrarı (M-02/H-02)."""
    return hashlib.sha256(image_bytes).hexdigest()


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
    plan_name: str = "",
    day_theme: str = "",
    task_context: str = "",
    previous_content_hashes: list[str] | None = None,
) -> ProofResult:
    image_bytes = prepare_upload(image_bytes, mime_type)
    content_hash = image_content_hash(image_bytes)
    known = {digest for digest in (previous_content_hashes or []) if digest}
    if content_hash in known:
        raise ProofRejected(
            "Aynı kareyi tekrar almışım gibi duruyor. Yeni bir kare çeker misin?"
        )

    # H-02: 3. denemede de Vision çalışır. Beyan yolu yalnız Vision skoru
    # eşiğin altında kaldığında açılır — erken return yok.
    try:
        data = await generate_json_with_image(
            prompt=prompts.PROOF_VALIDATION_PROMPT.format(
                task_title=task_title,
                tiny_version=tiny_version or "belirtilmedi",
                categories=", ".join(categories or []) or "belirtilmedi",
                task_type=task_type,
                plan_name=plan_name or "belirtilmedi",
                day_theme=day_theme or "belirtilmedi",
                task_context=task_context or "yok",
            ),
            image_bytes=image_bytes,
            mime_type=mime_type,
            # faz8.13: şema artık çağrı bazlı — kanıt kendi şemasını geçirir.
            response_schema=PROOF_RESPONSE_SCHEMA,
        )
    except GeminiUnavailable as exc:
        msg = str(exc).casefold()
        if "invalid_argument" in msg and (
            "image" in msg or "process input" in msg or "unable to process" in msg
        ):
            raise ProofRejected(
                "Fotoğraf okunamadı veya işlenemedi. Yeni bir kare çekip tekrar dener misin?"
            ) from exc
        # Geçici Vision hatası: beyanla onay YOK — 503, deneme yakılmaz.
        raise

    try:
        confidence = max(0, min(100, int(data.get("confidence") or 0)))
    except (TypeError, ValueError):
        confidence = 0
    if has_location:
        confidence = min(100, confidence + 10)

    approved = confidence >= settings.PROOF_MIN_CONFIDENCE
    accepted_by_declaration = False
    reason = str(data.get("reason") or "")
    if not approved and attempt_no >= settings.PROOF_MAX_ATTEMPTS:
        # §1.5: kullanıcıyla savaşma — görevi kabul et, gerçek skoru sakla.
        approved = True
        accepted_by_declaration = True
        reason = (
            "Tam emin olamadım; yine de 3. denemede beyanınla kabul ettim. 🌙"
        )
    elif not approved:
        reason = "Tam emin olamadım, bir kare daha dener misin? " + reason

    return ProofResult(
        approved=approved,
        confidence=confidence,
        reason=reason,
        attempt_no=attempt_no,
        accepted_by_declaration=accepted_by_declaration,
        content_hash=content_hash,
    )
