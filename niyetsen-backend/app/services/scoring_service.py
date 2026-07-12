"""
Niyetsen — Puan/Ceza/Zincir Motoru (uygulamanın kalbi)
======================================================
SAF MANTIK: burada DB yok, HTTP yok, AI yok. GameState alır, GameState + event
listesi döndürür. Bu yüzden %100 birim-testlenebilir (tests/test_scoring.py).

Kurallar MASTER_PLAN §1.2–1.3'ten birebir:
- Görev +50 (etiketli her kategoriye)
- Sessiz kaçırma: 25 × 2^n, TAVAN 200; herhangi bir tamamlama sayacı sıfırlar
- Mazeret yolu: sabit 25, katlanmaz, sayaç sıfırlanır; 10. mazerette ×0.5
- Puan tabanı 0 (asla negatif değil)
- Zincir: günde ≥1 görev = devam; boş günde jeton varsa otomatik harcanır
"""
from __future__ import annotations

from datetime import date

from app.config import (
    BASE_PENALTY,
    BONUS_POINTS,
    CATEGORIES,
    EXCUSE_LIMIT,
    EXCUSE_PENALTY,
    FREEZE_TOKENS_PER_MONTH,
    POINTS_FLOOR,
    POINTS_PER_TASK,
    RANK_LADDER,
    RANK_UNRANKED,
    SILENT_PENALTY_CAP,
)
from app.models.schemas import GameState, ScoreEvent


# ---------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------
def _apply(state: GameState, category: str, delta: int, reason: str,
           events: list[ScoreEvent]) -> None:
    """Tek kategoriye puan uygula; taban 0 kuralını burada zorla."""
    if category not in state.points:
        return  # bilinmeyen kategori sessizce yok sayılır (model uydurursa)
    old = state.points[category]
    new = max(POINTS_FLOOR, old + delta)
    state.points[category] = new
    events.append(ScoreEvent(category=category, delta=new - old, reason=reason))


def silent_penalty_amount(silent_miss_streak: int) -> int:
    """Sessiz kaçırma cezası: 25 → 50 → 100 → 200 (TAVAN)."""
    return min(BASE_PENALTY * (2 ** silent_miss_streak), SILENT_PENALTY_CAP)


def rank_for(points: int) -> str:
    for threshold, name in RANK_LADDER:
        if points >= threshold:
            return name
    return RANK_UNRANKED


def overall_rank(points: dict[str, int]) -> str:
    """Genel rütbe = 6 kategorinin ortalamasının kademesi."""
    avg = sum(points.get(c, 0) for c in CATEGORIES) // len(CATEGORIES)
    return rank_for(avg)


# ---------------------------------------------------------------
# Görev olayları
# ---------------------------------------------------------------
def complete_task(state: GameState, categories: list[str]) -> list[ScoreEvent]:
    """Görev tamamlandı: her etiketli kategoriye +50; sessiz kaçırma sayacı sıfır."""
    events: list[ScoreEvent] = []
    for c in categories:
        _apply(state, c, POINTS_PER_TASK, "görev tamamlandı", events)
    state.silent_miss_streak = 0
    return events


def complete_bonus(state: GameState, category: str) -> list[ScoreEvent]:
    """FAZ 4 micro-task: one category gets +10; it is not a plan completion."""
    events: list[ScoreEvent] = []
    _apply(state, category, BONUS_POINTS, "motivasyon bonus görevi", events)
    return events


def miss_task_silent(state: GameState, categories: list[str]) -> list[ScoreEvent]:
    """Açıklamasız kaçırma: katlanan ceza (tavanlı), sonra sayaç artar."""
    events: list[ScoreEvent] = []
    penalty = silent_penalty_amount(state.silent_miss_streak)
    for c in categories:
        _apply(state, c, -penalty, f"sessiz kaçırma (x{2 ** state.silent_miss_streak})", events)
    state.silent_miss_streak += 1
    return events


def miss_task_excused(state: GameState, categories: list[str]) -> list[ScoreEvent]:
    """
    Mazeret yolu: dürüst bildirim ödüllendirilir — ceza sabit 25, katlanma
    sayacı sıfırlanır. Ama sınırsız da değil: 10. mazerette tüm puan yarıya.
    """
    events: list[ScoreEvent] = []
    for c in categories:
        _apply(state, c, -EXCUSE_PENALTY, "mazeretli erteleme", events)
    state.silent_miss_streak = 0
    state.excuse_count += 1

    if state.excuse_count >= EXCUSE_LIMIT:
        for c in CATEGORIES:
            half_loss = -(state.points[c] // 2)
            if half_loss:
                _apply(state, c, half_loss, "10 mazeret eşiği: puan ×0.5", events)
        state.excuse_count = 0
    return events


# ---------------------------------------------------------------
# Zincir (streak) — gün sonu işlemi
# ---------------------------------------------------------------
def grant_monthly_freeze(state: GameState, today: date) -> bool:
    """Ay başında 1 Zincir Koruma Jetonu ver (aynı ay içinde tekrar verme)."""
    month_key = today.strftime("%Y-%m")
    if state.freeze_last_grant != month_key:
        state.freeze_tokens += FREEZE_TOKENS_PER_MONTH
        state.freeze_last_grant = month_key
        return True
    return False


def close_day(state: GameState, day: date, any_task_completed: bool) -> str:
    """
    Gün sonu cron'unun çağırdığı zincir kapanışı. Dönen değer bildirim tonunu
    seçmek için: 'extended' | 'frozen' | 'broken' | 'noop'
    NOT: kullanıcı timezone'unda 23:59'da çağrılır (routes -> cron).
    """
    grant_monthly_freeze(state, day)

    if state.last_active_date == day:
        return "noop"  # aynı gün iki kez kapatılamaz

    if any_task_completed:
        # dünden (veya jetonla korunmuş dünden) devam mı, yeni başlangıç mı?
        if state.last_active_date is not None and (day - state.last_active_date).days == 1:
            state.streak_len += 1
        else:
            state.streak_len = 1
        state.last_active_date = day
        state.best_streak = max(state.best_streak, state.streak_len)
        return "extended"

    # Hiç görev yok: jeton varsa zinciri koru
    if state.freeze_tokens > 0 and state.streak_len > 0:
        state.freeze_tokens -= 1
        state.last_active_date = day  # gün "korunmuş" sayılır
        return "frozen"

    # Zincir kırıldı — ton: "yarın yeni bir halka", ASLA suçlama (philosophy.py)
    state.streak_len = 0
    state.last_active_date = day
    return "broken"
