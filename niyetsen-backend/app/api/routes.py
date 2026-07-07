"""
Niyetsen — API Rotaları
Kimlik: dev'de X-User-Id başlığı (AUTH_DISABLED=true iken); prod'da Supabase JWT
zorunlu (get_current_user içindeki yuva). JWT'siz endpoint yok (health hariç).
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from datetime import date

import jwt
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile

from app.config import CATEGORIES, settings
from app.core.gemini_client import GeminiUnavailable
from app.models.schemas import (
    ChatRequest, ChatResponse, Plan, PlanGenerateRequest, ProofResult, StateResponse,
)
from app.services import intent_service, plan_service, proof_service, scoring_service
from app.storage.repository import repo

log = logging.getLogger("niyetsen.api")
router = APIRouter()

GEMINI_DOWN_MSG = "Şu an yıldızlara ulaşamıyorum, birazdan tekrar dener misin? ✨"


# ------------------------------------------------------------------
# Kimlik
# ------------------------------------------------------------------
AUTH_ERROR = HTTPException(status_code=401, detail="Kimlik doğrulama gerekli.")


def get_current_user(
    x_user_id: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> str:
    if settings.AUTH_DISABLED:
        return x_user_id or "demo"

    if not authorization or not authorization.lower().startswith("bearer "):
        raise AUTH_ERROR
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError:
        raise AUTH_ERROR

    user_id = payload.get("sub")
    if not user_id:
        raise AUTH_ERROR
    return user_id


# ------------------------------------------------------------------
# Basit bellek-içi rate limit (kullanıcı başına N istek/dk) — /chat için.
# Cursor notu: çok-instance prod'da Redis tabanlıya geçir; arayüz aynı kalsın.
# ------------------------------------------------------------------
_hits: dict[str, deque] = defaultdict(deque)


def rate_limit_chat(user_id: str = Depends(get_current_user)) -> str:
    now = time.time()
    q = _hits[user_id]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= settings.CHAT_RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Biraz nefes al 🌙 (dakikalık sınır)")
    q.append(now)
    return user_id


# ------------------------------------------------------------------
# Endpoint'ler
# ------------------------------------------------------------------
@router.get("/health")
def health() -> dict:
    return {"status": "ok", "env": settings.ENV, "model": settings.GEMINI_MODEL}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user_id: str = Depends(rate_limit_chat)) -> ChatResponse:
    """Çekirdek halka 1/2: niyet toplama sohbeti."""
    state = repo.get_state(user_id)
    try:
        return await intent_service.handle_chat(req, state=state)
    except GeminiUnavailable:
        raise HTTPException(status_code=503, detail=GEMINI_DOWN_MSG)


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
    user_id: str = Depends(get_current_user),
) -> ProofResult:
    """Foto kanıt: Vision skoru → onay → puan. In-app kamera zorunluluğu mobilde."""
    task = repo.get_task(user_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")
    if task.status == "done":
        raise HTTPException(status_code=409, detail="Bu görev zaten tamamlandı.")

    image_bytes = await photo.read()
    mime_type = photo.content_type or ""
    try:
        proof_service.validate_upload(image_bytes, mime_type)
    except proof_service.ProofRejected as e:
        # Geçersiz dosya (yanlış tip/boyut) bir "deneme hakkı" yakmaz.
        raise HTTPException(status_code=400, detail=str(e))

    attempt = repo.incr_proof_attempts(user_id, task_id)
    try:
        result = await proof_service.evaluate_proof(
            task_title=task.title,
            image_bytes=image_bytes,
            mime_type=mime_type,
            attempt_no=attempt,
            has_location=has_location,
        )
    except proof_service.ProofRejected as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result.approved:
        state = repo.get_state(user_id)
        scoring_service.complete_task(state, task.categories)
        repo.save_state(state)
        task.status = "done"
        repo.update_task(user_id, task)
    return result


@router.post("/task/{task_id}/excuse")
def excuse_task(task_id: str, user_id: str = Depends(get_current_user)) -> dict:
    """Mazeret yolu: chat'teki gorev_ertele_mazeretli aracı da buraya düşer."""
    task = repo.get_task(user_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")
    if task.status != "pending":
        raise HTTPException(status_code=409, detail="Görev zaten sonuçlanmış.")
    state = repo.get_state(user_id)
    events = scoring_service.miss_task_excused(state, task.categories)
    repo.save_state(state)
    task.status = "missed_excused"
    repo.update_task(user_id, task)
    return {
        "message": "Dürüstlüğün için teşekkürler — ceza sabit kaldı, katlanma sıfırlandı. "
                   "İstersen bugünün en küçük halkasını yine de koyabilirsin. 🌙",
        "events": [e.model_dump() for e in events],
    }


@router.post("/cron/close-day")
def close_day(day: date | None = None, user_id: str = Depends(get_current_user)) -> dict:
    """
    Gün sonu (kullanıcı timezone 23:59): tamamlanmayan görevlere sessiz ceza,
    zincir kapanışı. Cursor notu (v1): bu, TÜM kullanıcılar için zamanlanmış
    işten çağrılır (Railway cron / APScheduler); burada tek kullanıcı sürümü.
    """
    day = day or date.today()
    state = repo.get_state(user_id)
    plan = repo.get_plan(user_id)

    any_completed = False
    penalized = 0
    if plan:
        for d in plan.days:
            for t in d.tasks:
                if t.date == day:
                    if t.status == "done":
                        any_completed = True
                    elif t.status == "pending":
                        scoring_service.miss_task_silent(state, t.categories)
                        t.status = "missed_silent"
                        repo.update_task(user_id, t)
                        penalized += 1

    streak_result = scoring_service.close_day(state, day, any_completed)
    repo.save_state(state)
    return {"streak": streak_result, "penalized_tasks": penalized,
            "streak_len": state.streak_len, "freeze_tokens": state.freeze_tokens}


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
