"""
Niyetsen — API Rotaları
Kimlik: dev'de X-User-Id başlığı (AUTH_DISABLED=true iken); prod'da Supabase JWT
zorunlu (get_current_user içindeki yuva). JWT'siz endpoint yok (health hariç).
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import date, datetime, timezone

import jwt
from fastapi import (
    APIRouter, Depends, File, Form, Header, HTTPException, Request, Response,
    UploadFile,
)
from jwt import PyJWKClient

from app.config import CATEGORIES, settings
from app.core.gemini_client import GeminiUnavailable
from app.core.rate_limit import limiter
from app.models.schemas import (
    ChatMessage, ChatRequest, ChatResponse, ChatSessionResponse, Plan,
    PlanGenerateRequest, ProfileUpdate, ProofRecord, ProofResult, StateResponse,
    UserProfile,
)
from app.services import (
    intent_service, plan_service, profile_service, proof_service, scoring_service,
    task_lifecycle_service, tool_service,
)
from app.storage.repository import repo

log = logging.getLogger("niyetsen.api")
router = APIRouter()

GEMINI_DOWN_MSG = "Şu an yıldızlara ulaşamıyorum, birazdan tekrar dener misin? ✨"


def _legacy_message_id(user_id: str, index: int, role: str, content: str) -> str:
    digest = hashlib.sha256(
        f"{user_id}:{index}:{role}:{content}".encode()
    ).hexdigest()[:24]
    return f"legacy-{digest}"


# ------------------------------------------------------------------
# Kimlik
# ------------------------------------------------------------------
AUTH_ERROR = HTTPException(status_code=401, detail="Kimlik doğrulama gerekli.")

# Supabase artık HS256 legacy secret yerine JWKS (RS256/ES256) ile imzalıyor;
# anahtarlar Supabase tarafında rotate edilebildiği için burada cache'lenip
# kid üzerinden çözülüyor (PyJWKClient kendi içinde cache'liyor).
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")
    return _jwks_client


def get_current_user(
    x_user_id: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> str:
    # Dev kolaylığı: bearer yoksa X-User-Id kabul edilir. Gerçek bir bearer
    # gönderildiyse AUTH_DISABLED açık olsa bile doğrula; böylece mobil auth
    # entegrasyonu production kilidini açmadan güvenle test edilir.
    if settings.AUTH_DISABLED and not authorization:
        return x_user_id or "demo"

    if not authorization or not authorization.lower().startswith("bearer "):
        raise AUTH_ERROR
    token = authorization.split(" ", 1)[1].strip()
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
        )
    except Exception as exc:
        log.warning("JWT doğrulama başarısız: %s", exc)
        raise AUTH_ERROR

    user_id = payload.get("sub")
    if not user_id:
        raise AUTH_ERROR
    return user_id


# ------------------------------------------------------------------
# Endpoint'ler
# ------------------------------------------------------------------
@router.get("/health")
def health() -> dict:
    return {"status": "ok", "env": settings.ENV, "model": settings.GEMINI_MODEL}


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(f"{settings.CHAT_RATE_LIMIT_PER_MIN}/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    user_id: str = Depends(get_current_user),
) -> ChatResponse:
    """Çekirdek halka 1/2: niyet toplama sohbeti."""
    state = repo.get_state(user_id)
    profile = repo.get_profile(user_id)
    active = repo.get_active_intent(user_id)
    active_intent = (
        active[0].model_dump_json(exclude_none=True)
        if active else ""
    )
    try:
        response = await intent_service.handle_chat(
            req,
            state=state,
            user_name=profile.name or "",
            birth_date=profile.birth_date.isoformat() if profile.birth_date else "",
            zodiac=profile.zodiac_sign or "",
            active_intent=active_intent,
        )
    except GeminiUnavailable:
        raise HTTPException(status_code=503, detail=GEMINI_DOWN_MSG)

    response.tool_calls, tool_messages = tool_service.dispatch(
        repo, user_id, response.tool_calls
    )
    if tool_messages:
        response.reply = f"{response.reply}\n\n" + " ".join(tool_messages)

    # İstemci bugün tüm geçmişi gönderiyor. Her mesajın kalıcı kimliği sayesinde
    # retry/eşzamanlı istekler ikinci kayıt oluşturmaz. Eski istemciler için
    # rol+metin+sıra tabanlı deterministik bir kimlik üretilir.
    for index, message in enumerate(req.messages):
        if not message.id:
            message = message.model_copy(update={
                "id": _legacy_message_id(
                    user_id, index, message.role, message.content
                )
            })
        repo.append_chat_message(user_id, message)

    assistant_id = _legacy_message_id(
        user_id, len(req.messages), "assistant", response.reply
    )
    response.message_id = assistant_id
    repo.append_chat_message(
        user_id,
        ChatMessage(id=assistant_id, role="assistant", content=response.reply),
    )
    repo.save_intent(
        user_id,
        response.collected,
        response.collected.duration_days or 365,
        response.ready_for_plan,
    )

    return response


@router.get("/chat/history", response_model=list[ChatMessage])
def chat_history(user_id: str = Depends(get_current_user)) -> list[ChatMessage]:
    """Uygulama yeniden açılınca / yeni cihazda sohbeti kaldığı yerden göstermek için."""
    return repo.get_chat_history(user_id)


@router.get("/chat/session", response_model=ChatSessionResponse)
def chat_session(user_id: str = Depends(get_current_user)) -> ChatSessionResponse:
    """Mesajlarla aktif niyet durumunu tek çağrıda hydrate eder."""
    active = repo.get_active_intent(user_id)
    collected, ready = active or (None, False)
    return ChatSessionResponse(
        messages=repo.get_chat_history(user_id),
        collected=collected or {},
        ready_for_plan=ready,
    )


@router.get("/plan", response_model=Plan)
def get_plan(user_id: str = Depends(get_current_user)) -> Plan:
    """Var olan planı OKUR (üretmez). Uygulama yeniden açılınca kaldığı yerden devam eder."""
    plan = repo.get_plan(user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Henüz bir planın yok. Önce /plan/generate.")
    return plan


@router.post("/plan/generate", response_model=Plan)
async def generate_plan(req: PlanGenerateRequest, user_id: str = Depends(get_current_user)) -> Plan:
    """Çekirdek halka 2/2: görselli plan (ilk parti). Sonraki partiler /plan/next."""
    try:
        plan = await plan_service.generate_batch(
            req.collected, duration_days=req.duration_days, start_date=date.today(),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except GeminiUnavailable:
        raise HTTPException(status_code=503, detail=GEMINI_DOWN_MSG)
    repo.save_plan(user_id, plan)
    repo.complete_active_intent(user_id)
    return plan


@router.post("/plan/next", response_model=Plan)
async def next_batch(req: PlanGenerateRequest, user_id: str = Depends(get_current_user)) -> Plan:
    """Partili üretim: mevcut planın kaldığı günden sonraki bölümü ekler."""
    current = repo.get_plan(user_id)
    if not current:
        raise HTTPException(status_code=404, detail="Önce /plan/generate ile plan oluştur.")
    if current.batch_generated_until >= current.duration_days:
        return current
    try:
        batch = await plan_service.generate_batch(
            req.collected,
            duration_days=current.duration_days,
            start_day=current.batch_generated_until + 1,
            start_date=current.start_date,  # aynı çapa: günler doğru takvim tarihine düşsün
        )
    except GeminiUnavailable:
        raise HTTPException(status_code=503, detail=GEMINI_DOWN_MSG)
    current.days.extend(batch.days)
    current.batch_generated_until = batch.batch_generated_until
    repo.save_plan(user_id, current)
    return current


@router.post("/task/{task_id}/proof", response_model=ProofResult)
async def upload_proof(
    task_id: str,
    photo: UploadFile = File(...),
    has_location: bool = Form(default=False),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    user_id: str = Depends(get_current_user),
) -> ProofResult:
    """Foto kanıt: Vision skoru → onay → puan. In-app kamera zorunluluğu mobilde."""
    task = repo.get_task(user_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")
    if task.status != "pending":
        raise HTTPException(status_code=409, detail="Bu görev zaten sonuçlandı.")

    image_bytes = await photo.read()
    mime_type = photo.content_type or ""
    try:
        proof_service.validate_upload(image_bytes, mime_type)
    except proof_service.ProofRejected as e:
        # Geçersiz dosya (yanlış tip/boyut) bir "deneme hakkı" yakmaz.
        raise HTTPException(status_code=400, detail=str(e))

    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Konum için enlem ve boylam birlikte gerekli.")
    if latitude is not None and not -90 <= latitude <= 90:
        raise HTTPException(status_code=422, detail="Enlem -90 ile 90 arasında olmalı.")
    if longitude is not None and not -180 <= longitude <= 180:
        raise HTTPException(status_code=422, detail="Boylam -180 ile 180 arasında olmalı.")
    effective_location = latitude is not None and longitude is not None
    attempt = repo.incr_proof_attempts(user_id, task_id)
    try:
        result = await proof_service.evaluate_proof(
            task_title=task.title,
            image_bytes=image_bytes,
            mime_type=mime_type,
            attempt_no=attempt,
            has_location=effective_location,
        )
    except proof_service.ProofRejected as e:
        raise HTTPException(status_code=400, detail=str(e))

    location = (
        {"latitude": latitude, "longitude": longitude}
        if effective_location else None
    )
    photo_url = repo.store_proof_photo(user_id, task_id, image_bytes, mime_type)
    proof = ProofRecord(
        id=str(uuid.uuid4()),
        task_id=task_id,
        photo_url=photo_url,
        location=location,
        confidence_score=result.confidence,
        attempt_no=attempt,
    )
    repo.save_proof(user_id, proof)
    result.proof_id = proof.id
    result.photo_url = photo_url

    if result.approved:
        try:
            task_lifecycle_service.approve_proof(repo, user_id, proof)
        except task_lifecycle_service.TaskAlreadyResolved as exc:
            raise HTTPException(status_code=409, detail=str(exc))
    return result


@router.post("/task/{task_id}/excuse")
def excuse_task(task_id: str, user_id: str = Depends(get_current_user)) -> dict:
    """Mazeret yolu: chat'teki gorev_ertele_mazeretli aracı da buraya düşer."""
    try:
        events = task_lifecycle_service.excuse_task(repo, user_id, task_id)
    except task_lifecycle_service.TaskNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except task_lifecycle_service.TaskAlreadyResolved as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {
        "message": "Dürüstlüğün için teşekkürler — ceza sabit kaldı, katlanma sıfırlandı. "
                   "İstersen bugünün en küçük halkasını yine de koyabilirsin. 🌙",
        "events": [e.model_dump() for e in events],
    }


def require_cron_secret(
    x_cron_secret: str | None = Header(default=None),
) -> None:
    if not settings.CRON_SECRET:
        raise HTTPException(status_code=503, detail="Cron sırrı yapılandırılmamış.")
    if not x_cron_secret or not secrets.compare_digest(
        x_cron_secret, settings.CRON_SECRET
    ):
        raise HTTPException(status_code=401, detail="Cron kimlik doğrulaması başarısız.")


@router.post("/cron/close-day")
def close_day(
    at: datetime | None = None,
    _: None = Depends(require_cron_secret),
) -> dict:
    """
    Her kullanıcı için kendi timezone'unda son kapanmış günü hesaplar. Endpoint
    kullanıcı JWT'si yerine yalnız sunucudaki cron sırrıyla çağrılır.
    """
    if at is not None and at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    return task_lifecycle_service.close_due_users(repo, at)


@router.get("/me/state", response_model=StateResponse)
def my_state(user_id: str = Depends(get_current_user)) -> StateResponse:
    """Rank ekranının tek çağrısı: puanlar + kademeler + zincir."""
    s = repo.get_state(user_id)
    return StateResponse(
        points=s.points,
        ranks={c: scoring_service.rank_for(s.points[c]) for c in CATEGORIES},
        overall_rank=scoring_service.overall_rank(s.points),
        streak_len=s.streak_len,
        best_streak=s.best_streak,
        freeze_tokens=s.freeze_tokens,
        excuse_count=s.excuse_count,
        silent_miss_streak=s.silent_miss_streak,
    )


@router.get("/me/profile", response_model=UserProfile)
def my_profile(user_id: str = Depends(get_current_user)) -> UserProfile:
    return repo.get_profile(user_id)


@router.put("/me/profile", response_model=UserProfile)
def update_profile(
    update: ProfileUpdate,
    user_id: str = Depends(get_current_user),
) -> UserProfile:
    current = repo.get_profile(user_id)
    try:
        profile = profile_service.build_profile(update, current)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    repo.save_profile(user_id, profile)
    return profile


@router.delete("/me", status_code=204)
def delete_my_account(user_id: str = Depends(get_current_user)) -> Response:
    try:
        repo.delete_account(user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return Response(status_code=204)
