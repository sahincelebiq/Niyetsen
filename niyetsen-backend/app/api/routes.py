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
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import jwt
from fastapi import (
    APIRouter, Depends, File, Form, Header, HTTPException, Request, Response,
    UploadFile,
)
from jwt import PyJWKClient

from app.config import BONUS_POINTS, CATEGORIES, settings
from app.core.gemini_client import GeminiUnavailable
from app.core.rate_limit import limiter
from app.models.schemas import (
    AttachmentIngestResponse, BonusCompletionRequest, BonusOfferResponse, ChatMessage,
    ChatGreetingResponse, ChatRequest, ChatResponse, ChatSessionResponse, CollectedIntent,
    ConsentStatus, ConsentUpdate, DailyTaskItem, Plan, PlanGenerateRequest, PlanRenameRequest,
    PlanSummary, ProfileUpdate, ProofRecord, ProofResult, PushTokenRecord,
    PushTokenRegistration, RevenueCatWebhookPayload, StateResponse, SubscriptionInfo,
    UserProfile,
)
from app.services import (
    attachment_service, bonus_service, consent_service, greeting_service, intent_service,
    notification_service, plan_service, profile_service, project_service,
    proof_service, push_service, scoring_service, subscription_service,
    task_lifecycle_service, tool_service,
)
from app.services.bonus_pool import is_completion_message
from app.storage.repository import repo

log = logging.getLogger("niyetsen.api")
router = APIRouter()

GEMINI_DOWN_MSG = "Şu an yıldızlara ulaşamıyorum, birazdan tekrar dener misin? ✨"
CONSENT_REQUIRED = {
    "chat": "Sohbet için güncel gizlilik, KVKK ve AI işleme onayları gerekli.",
    "proof": "Kanıt için güncel gizlilik, KVKK ve fotoğraf işleme onayları gerekli.",
}
PAYWALL_DETAIL = {
    "code": "paywall_required",
    "message": "7 günlük denemen sona erdi. Zincirini korumak için devam et.",
}
MULTI_PLAN_PAYWALL = {
    "code": "paywall_required",
    "message": "İkinci plan için abonelik gerekir. Devam etmek için paketi aç.",
}


def _require_consent(user_id: str, purpose: str) -> None:
    if not consent_service.allows(repo, user_id, purpose):
        raise HTTPException(
            status_code=403,
            detail={"code": "consent_required", "message": CONSENT_REQUIRED[purpose]},
        )


def _require_premium(user_id: str) -> SubscriptionInfo:
    subscription_service.sync_expired_trials(repo, user_id)
    info = subscription_service.get_subscription(repo, user_id)
    if not info.has_premium_access:
        raise HTTPException(status_code=402, detail=PAYWALL_DETAIL)
    return info


def _legacy_message_id(user_id: str, index: int, role: str, content: str) -> str:
    digest = hashlib.sha256(
        f"{user_id}:{index}:{role}:{content}".encode()
    ).hexdigest()[:24]
    return f"legacy-{digest}"


def _task_memory(user_id: str, timezone_name: str) -> tuple[str, str]:
    plan = repo.get_plan(user_id)
    if plan is None:
        return "Aktif plan yok", ""
    try:
        user_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        user_timezone = ZoneInfo("Europe/Istanbul")
    today = datetime.now(timezone.utc).astimezone(user_timezone).date()
    tasks = [task for day in plan.days for task in day.tasks]
    todays_tasks = [task for task in tasks if task.date == today]
    if todays_tasks:
        status_counts: dict[str, int] = {}
        for task in todays_tasks:
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
        today_status = ", ".join(
            f"{count} {status}" for status, count in sorted(status_counts.items())
        )
    else:
        today_status = "Bugüne atanmış görev yok"
    recent = sorted(
        (task for task in tasks if task.date and task.date <= today),
        key=lambda task: (task.date, task.day),
        reverse=True,
    )[:5]
    recent_tasks = "; ".join(
        f"{task.title} ({task.date.isoformat()}, {task.status})"
        for task in recent
    )
    return today_status, recent_tasks


def _recent_mood(messages: list[ChatMessage]) -> str:
    markers = (
        "hissediyorum", "hissediyordum", "moralim", "mutluyum", "üzgünüm",
        "kaygılı", "endişeli", "yorgunum", "enerjik", "stresli",
    )
    notes = [
        message.content.strip()[:240]
        for message in messages[-12:]
        if message.role == "user"
        and any(marker in message.content.casefold() for marker in markers)
    ]
    return " | ".join(notes[-2:])


def _user_today(timezone_name: str) -> date:
    try:
        target = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        target = ZoneInfo("Europe/Istanbul")
    return datetime.now(timezone.utc).astimezone(target).date()


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
    return {
        "status": "ok",
        "env": settings.ENV,
        "model_chat": settings.GEMINI_MODEL,
        "model_plan": settings.GEMINI_MODEL_PLAN,
    }


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(f"{settings.CHAT_RATE_LIMIT_PER_MIN}/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    user_id: str = Depends(get_current_user),
) -> ChatResponse:
    """Çekirdek halka 1/2: niyet toplama sohbeti."""
    _require_consent(user_id, "chat")
    _require_premium(user_id)
    state = repo.get_state(user_id)
    profile = repo.get_profile(user_id)
    active = repo.get_active_intent(user_id)
    active_intent = (
        active[0].model_dump_json(exclude_none=True)
        if active else ""
    )
    today_status, recent_tasks = _task_memory(user_id, profile.timezone)
    summaries = repo.list_plan_summaries(user_id)
    active_summary = next((item for item in summaries if item.is_active), None)
    plan_has_content = bool(active_summary and active_summary.has_content)
    last_user = next(
        (message for message in reversed(req.messages) if message.role == "user"),
        None,
    )
    active_bonus = repo.get_active_bonus(user_id)
    if (
        last_user is not None
        and active_bonus is not None
        and is_completion_message(last_user.content)
    ):
        completion_id = last_user.id or _legacy_message_id(
            user_id, len(req.messages) - 1, "user", last_user.content
        )
        awarded = bonus_service.complete(
            repo, user_id, active_bonus.id, completion_id
        )
        response = ChatResponse(
            reply=(
                f"Bonus halkayı tamamladın; {active_bonus.category} yönüne "
                f"+{BONUS_POINTS} puan eklendi."
                if awarded else
                "Bu bonus halka daha önce tamamlanmış; puanın ikinci kez değişmedi."
            ),
            ready_for_plan=req.collected.is_ready(),
            collected=req.collected,
        )
    else:
        try:
            response = await intent_service.handle_chat(
                req,
                state=state,
                user_name=profile.name or "",
                birth_date=profile.birth_date.isoformat() if profile.birth_date else "",
                zodiac=profile.zodiac_sign or "",
                active_intent=active_intent,
                today_status=today_status,
                recent_tasks=recent_tasks,
                mood_notes=_recent_mood(req.messages),
                has_active_plan=repo.get_plan(user_id) is not None,
                plan_has_content=plan_has_content,
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


@router.get("/chat/greeting", response_model=ChatGreetingResponse)
def chat_greeting(user_id: str = Depends(get_current_user)) -> ChatGreetingResponse:
    """Yeni sohbet veya boş oturumda saat dilimine göre kişiselleştirilmiş karşılama."""
    profile = repo.get_profile(user_id)
    message = greeting_service.build_chat_greeting(
        name=profile.name,
        timezone_name=profile.timezone,
    )
    return ChatGreetingResponse(message=message)


@router.get("/chat/session", response_model=ChatSessionResponse)
def chat_session(user_id: str = Depends(get_current_user)) -> ChatSessionResponse:
    """Mesajlarla aktif niyet durumunu tek çağrıda hydrate eder."""
    summaries = repo.list_plan_summaries(user_id)
    active_summary = next((item for item in summaries if item.is_active), None)
    plan_has_content = bool(active_summary and active_summary.has_content)
    active = repo.get_active_intent(user_id)
    collected, ready = active or (None, False)
    collected_intent = collected or CollectedIntent()
    can_generate = not plan_has_content and ready and collected_intent.is_ready()
    return ChatSessionResponse(
        messages=repo.get_chat_history(user_id),
        collected=collected_intent,
        ready_for_plan=can_generate,
        plan_has_content=plan_has_content,
        active_plan_name=active_summary.name if active_summary else "Planım",
    )


@router.post("/chat/attachment", response_model=AttachmentIngestResponse)
@limiter.limit(f"{settings.CHAT_RATE_LIMIT_PER_MIN}/minute")
async def ingest_chat_attachment(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
) -> AttachmentIngestResponse:
    """PDF/DOCX metin çıkarımı veya PNG/JPEG kısa görsel özeti."""
    _require_consent(user_id, "chat")
    _require_premium(user_id)
    data = await file.read()
    mime_type = file.content_type or ""
    filename = file.filename or "ek"
    try:
        attachment_service.validate_attachment(data, mime_type)
    except attachment_service.AttachmentRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    try:
        summary = await attachment_service.ingest_attachment(data, mime_type, filename)
    except attachment_service.AttachmentRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except GeminiUnavailable:
        raise HTTPException(status_code=503, detail=GEMINI_DOWN_MSG)
    return AttachmentIngestResponse(
        filename=filename,
        summary=summary,
        mime_type=mime_type.split(";")[0].strip().lower(),
    )


@router.get("/projects", response_model=list[PlanSummary])
def list_projects(user_id: str = Depends(get_current_user)) -> list[PlanSummary]:
    return project_service.list_projects(repo, user_id)


@router.post("/projects/new", response_model=PlanSummary)
def start_new_project(user_id: str = Depends(get_current_user)) -> PlanSummary:
    try:
        return project_service.start_new_project(repo, user_id)
    except PermissionError:
        raise HTTPException(status_code=402, detail=MULTI_PLAN_PAYWALL)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        log.exception("start_new_project failed user_id=%s", user_id)
        if repo.count_completed_plans(user_id) >= 1:
            raise HTTPException(status_code=402, detail=MULTI_PLAN_PAYWALL)
        raise HTTPException(
            status_code=500,
            detail="Yeni niyet başlatılamadı. Birazdan tekrar dener misin?",
        )


@router.put("/projects/{plan_id}/activate", response_model=PlanSummary)
def activate_project(plan_id: str, user_id: str = Depends(get_current_user)) -> PlanSummary:
    try:
        return project_service.activate_project(repo, user_id, plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/projects/{plan_id}", response_model=PlanSummary)
def rename_project(
    plan_id: str,
    body: PlanRenameRequest,
    user_id: str = Depends(get_current_user),
) -> PlanSummary:
    try:
        return project_service.rename_project(repo, user_id, plan_id, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/tasks/daily", response_model=list[DailyTaskItem])
def daily_tasks(user_id: str = Depends(get_current_user)) -> list[DailyTaskItem]:
    return project_service.get_today_tasks(repo, user_id)


@router.get("/plan", response_model=Plan)
def get_plan(user_id: str = Depends(get_current_user)) -> Plan:
    """Var olan planı OKUR (üretmez). Uygulama yeniden açılınca kaldığı yerden devam eder."""
    plan = repo.get_plan(user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Henüz bir planın yok. Önce /plan/generate.")
    return plan


@router.post("/plan/generate", response_model=Plan)
@limiter.limit(f"{settings.PLAN_RATE_LIMIT_PER_MIN}/minute")
async def generate_plan(
    request: Request,
    req: PlanGenerateRequest,
    user_id: str = Depends(get_current_user),
) -> Plan:
    """Çekirdek halka 2/2: görselli plan (ilk parti). Sonraki partiler /plan/next."""
    _require_consent(user_id, "chat")
    _require_premium(user_id)
    summaries = repo.list_plan_summaries(user_id)
    active = next((item for item in summaries if item.is_active), None)
    if active and active.has_content:
        raise HTTPException(
            status_code=409,
            detail="Bu niyet için plan zaten oluşturulmuş. Yeni plan için yeni niyet başlat.",
        )
    try:
        plan = await plan_service.generate_batch(
            req.collected, duration_days=req.duration_days, start_date=date.today(),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except GeminiUnavailable:
        raise HTTPException(status_code=503, detail=GEMINI_DOWN_MSG)
    if active:
        plan = plan.model_copy(
            update={
                "id": active.id,
                "name": active.name,
                "slot_no": active.slot_no,
                "is_active": True,
            }
        )
    repo.save_plan(user_id, plan)
    repo.complete_active_intent(user_id)
    subscription_service.start_trial_if_needed(repo, user_id)
    return plan


@router.post("/plan/next", response_model=Plan)
async def next_batch(req: PlanGenerateRequest, user_id: str = Depends(get_current_user)) -> Plan:
    """Partili üretim: mevcut planın kaldığı günden sonraki bölümü ekler."""
    _require_premium(user_id)
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
@limiter.limit(f"{settings.PROOF_RATE_LIMIT_PER_MIN}/minute")
async def upload_proof(
    request: Request,
    task_id: str,
    photo: UploadFile = File(...),
    has_location: bool = Form(default=False),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    x_idempotency_key: str | None = Header(default=None),
    user_id: str = Depends(get_current_user),
) -> ProofResult:
    """Foto kanıt: Vision skoru → onay → puan. In-app kamera zorunluluğu mobilde."""
    _require_consent(user_id, "proof")
    _require_premium(user_id)
    task = repo.get_task(user_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")

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
    idempotency_key = x_idempotency_key or hashlib.sha256(
        image_bytes
        + repr((latitude, longitude)).encode()
    ).hexdigest()
    try:
        claim = repo.begin_proof_attempt(user_id, task_id, idempotency_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if claim.status == "completed" and claim.result is not None:
        return claim.result
    if claim.status == "in_progress":
        raise HTTPException(
            status_code=409,
            detail="Bu görev için bir kanıt isteği hâlen işleniyor.",
        )

    try:
        result = await proof_service.evaluate_proof(
            task_title=task.title,
            image_bytes=image_bytes,
            mime_type=mime_type,
            attempt_no=claim.attempt_no,
            has_location=effective_location,
            tiny_version=task.tiny_version,
            categories=task.categories,
            task_type=task.task_type,
        )
    except GeminiUnavailable:
        repo.abort_proof_attempt(user_id, task_id, idempotency_key)
        raise HTTPException(status_code=503, detail=GEMINI_DOWN_MSG)
    except proof_service.ProofRejected as e:
        repo.abort_proof_attempt(user_id, task_id, idempotency_key)
        raise HTTPException(status_code=400, detail=str(e))

    if not result.approved:
        # Reddedilen hassas fotoğrafı Storage'a veya proofs tablosuna yazma.
        repo.finish_proof_attempt(user_id, task_id, idempotency_key, result)
        return result

    location = (
        {"latitude": latitude, "longitude": longitude}
        if effective_location else None
    )
    try:
        photo_url = repo.store_proof_photo(user_id, task_id, image_bytes, mime_type)
        proof = ProofRecord(
            id=str(uuid.uuid4()),
            task_id=task_id,
            photo_url=photo_url,
            location=location,
            confidence_score=result.confidence,
            attempt_no=claim.attempt_no,
        )
        repo.save_proof(user_id, proof)
        result.proof_id = proof.id
        result.photo_url = photo_url
        task_lifecycle_service.approve_proof(repo, user_id, proof)
    except task_lifecycle_service.TaskAlreadyResolved as exc:
        repo.abort_proof_attempt(user_id, task_id, idempotency_key)
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception:
        repo.abort_proof_attempt(user_id, task_id, idempotency_key)
        raise
    repo.finish_proof_attempt(user_id, task_id, idempotency_key, result)
    return result


@router.post("/task/{task_id}/excuse")
def excuse_task(task_id: str, user_id: str = Depends(get_current_user)) -> dict:
    """Mazeret yolu: chat'teki gorev_ertele_mazeretli aracı da buraya düşer."""
    _require_premium(user_id)
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
    result = task_lifecycle_service.close_due_users(repo, at)
    try:
        result["penalty_notifications_sent"] = (
            notification_service.send_penalty_notifications(
                repo, result.get("results", [])
            )
        )
    except Exception as exc:
        log.exception("Ceza bildirimleri gönderilemedi")
        result["penalty_notifications_sent"] = 0
        result["penalty_notification_error"] = str(exc)[:300]
    return result


@router.post("/cron/notifications")
def run_notifications(
    at: datetime | None = None,
    _: None = Depends(require_cron_secret),
) -> dict:
    if at is not None and at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    return notification_service.run_due_notifications(repo, at)


@router.post("/me/push-token", status_code=204)
def register_push_token(
    registration: PushTokenRegistration,
    user_id: str = Depends(get_current_user),
) -> Response:
    if not push_service.is_valid_expo_token(registration.token):
        raise HTTPException(status_code=422, detail="Geçersiz Expo push token.")
    repo.upsert_push_token(PushTokenRecord(
        user_id=user_id,
        token=registration.token,
        platform=registration.platform,
    ))
    return Response(status_code=204)


@router.delete("/me/push-token", status_code=204)
def unregister_push_token(
    token: str,
    user_id: str = Depends(get_current_user),
) -> Response:
    repo.disable_push_token(user_id, token)
    return Response(status_code=204)


@router.post("/bonus/offer", response_model=BonusOfferResponse)
def offer_bonus(
    user_id: str = Depends(get_current_user),
) -> BonusOfferResponse:
    _require_premium(user_id)
    profile = repo.get_profile(user_id)
    return bonus_service.offer_for_day(
        repo, user_id, _user_today(profile.timezone)
    )


@router.get("/bonus/active", response_model=BonusOfferResponse | None)
def get_active_bonus(
    user_id: str = Depends(get_current_user),
) -> BonusOfferResponse | None:
    _require_premium(user_id)
    return bonus_service.active_offer(repo, user_id)


@router.post("/bonus/{offer_id}/complete")
def complete_bonus(
    offer_id: str,
    completion: BonusCompletionRequest,
    user_id: str = Depends(get_current_user),
) -> dict:
    _require_premium(user_id)
    if not bonus_service.complete(
        repo, user_id, offer_id, completion.completion_id
    ):
        raise HTTPException(
            status_code=409,
            detail="Bonus görev bulunamadı veya daha önce tamamlandı.",
        )
    return {"awarded": BONUS_POINTS}


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
    if update.kvkk_consent and profile.kvkk_consent_at:
        consent_service.migrate_legacy_onboarding(
            repo, user_id, profile.kvkk_consent_at
        )
    return profile


@router.get("/me/subscription", response_model=SubscriptionInfo)
def my_subscription(user_id: str = Depends(get_current_user)) -> SubscriptionInfo:
    return subscription_service.sync_expired_trials(repo, user_id)


@router.post("/me/subscription/sync", response_model=SubscriptionInfo)
@limiter.limit("12/minute")
async def sync_my_subscription(
    request: Request,
    user_id: str = Depends(get_current_user),
) -> SubscriptionInfo:
    """Satın alma sonrası RevenueCat REST ile backend'i hizalar (webhook yedek)."""
    return await subscription_service.sync_from_revenuecat(repo, user_id)


@router.post("/webhooks/revenuecat", response_model=SubscriptionInfo)
async def revenuecat_webhook(
    payload: RevenueCatWebhookPayload,
    authorization: str | None = Header(default=None),
) -> SubscriptionInfo:
    secret = settings.REVENUECAT_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook sırrı yapılandırılmamış.")
    expected = f"Bearer {secret}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Geçersiz webhook sırrı.")
    event = payload.event or {}
    app_user_id = event.get("app_user_id")
    event_type = event.get("type", "")
    if not app_user_id:
        raise HTTPException(status_code=422, detail="app_user_id gerekli.")
    expiration_ms = event.get("expiration_at_ms")
    expiration_at = (
        datetime.fromtimestamp(expiration_ms / 1000, tz=timezone.utc)
        if expiration_ms else None
    )
    log.info(
        "RevenueCat webhook: type=%s user=%s",
        event_type,
        app_user_id,
    )
    return subscription_service.apply_revenuecat_event(
        repo,
        app_user_id=app_user_id,
        event_type=event_type,
        expiration_at=expiration_at,
    )


@router.get("/me/consent", response_model=ConsentStatus)
def get_my_consent(user_id: str = Depends(get_current_user)) -> ConsentStatus:
    profile = repo.get_profile(user_id)
    if profile.kvkk_consent_at:
        consent_service.migrate_legacy_onboarding(
            repo, user_id, profile.kvkk_consent_at
        )
    return consent_service.status(repo, user_id)


@router.post("/me/consent", response_model=ConsentStatus)
def update_my_consent(
    update: ConsentUpdate,
    user_id: str = Depends(get_current_user),
) -> ConsentStatus:
    result = consent_service.update(repo, user_id, update)
    if result.kvkk_explicit_consent.accepted:
        profile = repo.get_profile(user_id)
        if profile.kvkk_consent_at is None:
            profile.kvkk_consent_at = result.kvkk_explicit_consent.decided_at
            profile.onboarding_complete = bool(
                profile.name and profile.birth_date
            )
            repo.save_profile(user_id, profile)
    return result


@router.delete("/me", status_code=204)
def delete_my_account(user_id: str = Depends(get_current_user)) -> Response:
    try:
        repo.delete_account(user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return Response(status_code=204)
