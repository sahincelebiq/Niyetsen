"""
Niyetsen Raporu ("Wrapped") — FAZ 8.8 iskeleti (2026-07-29, yatırımcı talebi).
Spotify'ın yıllık özeti gibi: 14 günlük / aylık dönem sonunda kullanıcıya
story kartlarıyla "neler başardın" gösterilir.

Tasarım kararları:
- Kural bazlı, Gemini ÇAĞRILMAZ (hız + kota; kişisel cümle v2'de eklenebilir).
- Veri kaynağı: aktif plan görevleri + GameState. Çoklu plan toplaması Cursor
  detayı (docs/FAZ8_LANSMAN.md 8.8).
- Ton: kutlama + kimlik; utandırma YASAK. Kaçırılan görev sayısı gösterilmez,
  yalnız kazanımlar anlatılır (Wrapped mantığı — Spotify da az dinlediğini yüzüne
  vurmaz).
"""
from __future__ import annotations

from datetime import date, timedelta

from app.config import CATEGORIES
from app.models.schemas import GameState, Plan, RecapCard, RecapResponse
from app.services.scoring_service import overall_rank, rank_for

PERIOD_DAYS = {"7d": 7, "14d": 14, "30d": 30}


def _done_tasks_in_period(plans: list[Plan], start: date, end: date) -> list:
    """Dönem içinde tamamlanan görevler — TÜM planlardan (FAZ 8.9 gerçek veri)."""
    return [
        task
        for plan in plans
        for day in plan.days
        for task in day.tasks
        if task.status == "done" and task.date and start <= task.date <= end
    ]


def _top_category(points: dict[str, int]) -> tuple[str, int]:
    top = max(CATEGORIES, key=lambda c: points.get(c, 0))
    return top, points.get(top, 0)


def _period_top_category(done_tasks: list) -> tuple[str, int]:
    """Dönemin GERÇEK kategori dağılımı: tamamlanan görevlerin kategorileri.
    'Verilerimi raporlayamıyor' şikâyetinin çözümü — state toplamı değil,
    bu dönemde fiilen işlenen kategori sayılır."""
    counts: dict[str, int] = {}
    for task in done_tasks:
        for cat in task.categories:
            counts[cat] = counts.get(cat, 0) + 1
    if not counts:
        return "", 0
    top = max(counts, key=lambda c: counts[c])
    return top, counts[top]


def build_recap(
    *,
    state: GameState,
    plan: Plan | None,
    plans: list[Plan] | None = None,
    user_name: str = "",
    period: str = "14d",
    today: date | None = None,
) -> RecapResponse:
    """Story kartlarını üret. Saf fonksiyon — test edilebilir, yan etkisiz.

    FAZ 8.9: `plans` verilirse rapor TÜM planları toplar (çoklu plan gerçek
    veri); verilmezse eski davranış (yalnız aktif plan) korunur.
    """
    days = PERIOD_DAYS.get(period, 14)
    end = today or date.today()
    start = end - timedelta(days=days - 1)

    all_plans = [p for p in (plans if plans is not None else [plan]) if p is not None]
    if plan is None and all_plans:
        plan = all_plans[0]

    # Yolculuk = Niyetsen'deki İLK planın başlangıcından bugüne.
    earliest_start = min((p.start_date for p in all_plans), default=None)
    days_in = (end - earliest_start).days + 1 if earliest_start else 0

    done_tasks = _done_tasks_in_period(all_plans, start, end)
    completed = len(done_tasks)
    proofed = sum(1 for task in done_tasks if getattr(task, "proof_id", None))
    total_points = sum(state.points.get(c, 0) for c in CATEGORIES)
    top_cat, top_pts = _top_category(state.points)
    period_cat, period_cat_count = _period_top_category(done_tasks)
    name = (user_name or "").strip()

    first_theme = ""
    earliest_plan = min(all_plans, key=lambda p: p.start_date) if all_plans else None
    if earliest_plan and earliest_plan.days:
        day0 = earliest_plan.days[0]
        first_theme = (day0.theme or "").strip()
        if not first_theme and day0.tasks:
            first_theme = (day0.tasks[0].title or "").strip()
    journey_sub = (
        f"İlk gün: {first_theme[:80]}. Şimdi {max(days_in, 1)}. gündesin — "
        f"{completed} görev bu dönemde tamamlandı."
        if first_theme
        else f"Başladığın yerden {max(days_in, 1)}. güne. Bu dönemde {completed} görev."
    )

    cards: list[RecapCard] = [
        RecapCard(
            kind="intro",
            title=f"{name}, yolculuğun" if name else "Yolculuğun",
            headline=f"{max(days_in, 1)}. gün",
            subtitle=(
                f"{len(all_plans)} niyeti birden yürütüyorsun — her gün bir halka."
                if len(all_plans) > 1
                else "Niyetsen'e başladığından beri her gün bir halka."
            ),
        ),
        RecapCard(
            kind="journey",
            title="İlk gün → şimdi",
            headline=f"Gün 1 → Gün {max(days_in, 1)}",
            subtitle=journey_sub,
        ),
        RecapCard(
            kind="tasks",
            title=f"Son {days} gün",
            headline=f"{completed} görev",
            subtitle=(
                (
                    f"Tamamladın — {proofed}'ini fotoğrafla kanıtladın."
                    if proofed
                    else "Tamamladın — her biri karakterine işlendi."
                )
                if completed
                else "Yeni dönem temiz bir sayfa. İlk halka seni bekliyor."
            ),
        ),
        RecapCard(
            kind="trait",
            # FAZ 8.9: dönem-gerçek veri — bu dönemde fiilen işlenen kategori.
            # Dönem boşsa tüm zamanların puan lideri gösterilir.
            title="En çok gelişen yönün",
            headline=period_cat or top_cat,
            subtitle=(
                f"Bu dönem {period_cat_count} görev {period_cat}'e işledi · "
                f"toplam {state.points.get(period_cat, 0)} puan"
                if period_cat
                else f"{top_pts} puan · {rank_for(top_pts)} kademesi"
            ),
        ),
        RecapCard(
            kind="streak",
            title="Zincirin",
            headline=f"{state.best_streak} gün",
            subtitle=(
                f"En uzun serin. Şu an {state.streak_len} gündesin — devam."
                if state.streak_len
                else "En uzun serin. Yeni zincirin ilk halkası bugün olabilir."
            ),
        ),
        RecapCard(
            kind="closing",
            title="Genel rütben",
            headline=overall_rank(state.points),
            subtitle=f"Toplam {total_points} puan. Haftalık ve aylık raporun Zincir’de.",
        ),
    ]

    return RecapResponse(
        period=period,
        start_date=start,
        end_date=end,
        days_in=max(days_in, 0),
        completed_tasks=completed,
        total_points=total_points,
        top_category=top_cat,
        cards=cards,
    )


def is_recap_push_due(days_in: int) -> bool:
    """14. gün + sonrasında her 30 günde bir (14, 44, 74…)."""
    if days_in < 14:
        return False
    return (days_in - 14) % 30 == 0


def recap_push_period_days(days_in: int) -> int:
    """İlk rapor 14 günlük; sonrakiler aylık (30)."""
    return 14 if days_in == 14 else 30


def recap_push_body(days: int = 14) -> str:
    """Rapor hazır bildirimi — dürüst-sıcak ton (FAZ 8 ton kuralı)."""
    return (
        f"Son {days} günün hikâyesi hazır. "
        "Nereden nereye geldiğini gör — raporun seni bekliyor ✨"
    )
