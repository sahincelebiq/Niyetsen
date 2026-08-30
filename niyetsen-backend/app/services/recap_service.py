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
from zoneinfo import ZoneInfo

from app.config import CATEGORIES
from app.models.schemas import (
    GameState, Plan, PointLogRecord, RecapCard, RecapDashboard, RecapResponse,
)
from app.services.scoring_service import overall_rank, rank_for

PERIOD_DAYS = {"7d": 7, "14d": 14, "30d": 30}

_WEEKDAY_NAMES = (
    "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar",
)


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


def _mirror_line(
    all_plans: list[Plan],
    state: GameState,
    start: date,
    end: date,
) -> str:
    """Dürüst ayna: en güçlü/zayıf yön + erteleme örüntüsü. Sayıyla utandırma yok."""
    ranked = sorted(CATEGORIES, key=lambda c: state.points.get(c, 0))
    weak, strong = ranked[0], ranked[-1]
    period_tasks = [
        task
        for plan in all_plans
        for day in plan.days
        for task in day.tasks
        if task.date and start <= task.date <= end
    ]
    silent = sum(1 for t in period_tasks if t.status == "missed_silent")
    excused = sum(1 for t in period_tasks if t.status == "missed_excused")
    done = sum(1 for t in period_tasks if t.status == "done")
    if done == 0 and silent == 0 and excused == 0:
        return "Henüz yeterli iz yok. Birkaç kanıtlı gün sonra ayna netleşir."

    strong_pts = state.points.get(strong, 0)
    weak_pts = state.points.get(weak, 0)
    if strong_pts == weak_pts:
        trait = "Yönlerin henüz dengede"
    else:
        trait = f"{strong} büyüyor; {weak} daha ince kalmış"

    if silent > excused and silent > 0:
        habit = (
            "Takıldığın günlerde çoğu zaman sessizce geçtin — "
            "yüzleşme, zinciri korur."
        )
    elif excused > silent and excused > 0:
        habit = (
            "Takılınca haber veriyorsun; bu dürüstlük. "
            "Şimdi aynı dürüstlüğü göreve çevir."
        )
    elif done:
        habit = "Bu dönemde iz bıraktın — ritmi korumak özgüveni büyütür."
    else:
        habit = ""
    return f"{trait}. {habit}".strip()


def _hour_done_from_log(
    point_log: list[PointLogRecord] | None, tz_name: str
) -> list[int]:
    """+50 görev tamamlamalarının kullanıcı saat dilimindeki saat dağılımı."""
    if not point_log:
        return []
    try:
        tz = ZoneInfo(tz_name or "Europe/Istanbul")
    except Exception:  # noqa: BLE001 — bozuk TZ raporu düşürmesin
        tz = ZoneInfo("Europe/Istanbul")
    hours = [0] * 24
    hit = False
    for record in point_log:
        if record.delta <= 0 or not record.reason.startswith("görev tamamlandı"):
            continue
        created = record.created_at
        if created.tzinfo is None:
            from datetime import timezone as _tz

            created = created.replace(tzinfo=_tz.utc)
        hours[created.astimezone(tz).hour] += 1
        hit = True
    return hours if hit else []


def _build_insights(
    *,
    weekday_done: list[int],
    weekday_missed: list[int],
    hour_done: list[int],
    bonus_offered: int,
    bonus_completed: int,
    state: GameState,
) -> list[str]:
    """Dürüst, utandırmayan içgörü cümleleri (T8) — panel aynası, story değil.

    Öncelik sırası bilinçli: kaçan gün → üretken/sessiz saat → bonus →
    zayıf kategori → güçlü gün. En fazla 5 satır (panel şişmesin).
    """
    insights: list[str] = []

    if weekday_missed and max(weekday_missed) > 0:
        worst = weekday_missed.index(max(weekday_missed))
        insights.append(
            f"{_WEEKDAY_NAMES[worst]} günleri görev daha sık kaçıyor — "
            "o güne 2 dakikalık mini görev koy, zincir kopmasın."
        )
    if hour_done and sum(hour_done) >= 3:
        peak = hour_done.index(max(hour_done))
        insights.append(
            f"En üretken saatin {peak:02d}:00 civarı — kritik görevi o aralığa al."
        )
        awake = [(h, c) for h, c in enumerate(hour_done) if 8 <= h <= 22]
        if awake:
            quiet = min(awake, key=lambda hc: hc[1])
            if quiet[1] < max(hour_done):
                insights.append(
                    f"{quiet[0]:02d}:00 civarı genelde sessiz geçiyor — "
                    "oraya görev koyma ya da en küçük halkayı dene."
                )
    if bonus_offered:
        insights.append(
            f"{bonus_offered} bonus görev aldın, {bonus_completed} tanesini tamamladın."
        )
    ranked = sorted(CATEGORIES, key=lambda c: state.points.get(c, 0))
    weak, strong = ranked[0], ranked[-1]
    if state.points.get(strong, 0) > state.points.get(weak, 0):
        insights.append(
            f"{strong} yükselirken {weak} geride kalmış — "
            f"bu hafta bir {weak} görevini öne al."
        )
    if weekday_done and max(weekday_done) > 0:
        best = weekday_done.index(max(weekday_done))
        insights.append(
            f"En güçlü günün {_WEEKDAY_NAMES[best]} — zor görevleri oraya taşı."
        )
    return insights[:5]


def _build_dashboard(
    all_plans: list[Plan], state: GameState, days_in: int, end: date,
    start: date | None = None,
    *,
    point_log: list[PointLogRecord] | None = None,
    timezone_name: str = "",
    bonus_counts: tuple[int, int] | None = None,
) -> RecapDashboard:
    """faz8.13/3: ilk günden bugüne gerçek KPI'lar — kural bazlı, Gemini yok."""
    all_tasks = [
        task
        for plan in all_plans
        for day in plan.days
        for task in day.tasks
        if task.date and task.date <= end  # gelecek günler sayılmaz
    ]
    done = [t for t in all_tasks if t.status == "done"]
    proofed = sum(1 for t in done if getattr(t, "proof_id", None))
    category_counts: dict[str, int] = {c: 0 for c in CATEGORIES}
    for task in done:
        for cat in task.categories:
            if cat in category_counts:
                category_counts[cat] += 1
    total = len(all_tasks)
    rate = round(100 * len(done) / total) if total else 0
    # Gelişim eğrisi: son 8 haftanın tamamlanan görev sayıları (eski → yeni).
    weekly: list[int] = []
    for week in range(7, -1, -1):
        w_end = end - timedelta(days=7 * week)
        w_start = w_end - timedelta(days=6)
        weekly.append(
            sum(1 for t in done if t.date and w_start <= t.date <= w_end)
        )
    # T8 örüntüleri: hafta günü dağılımı (Pzt..Paz) — yapılan + kaçırılan.
    weekday_done = [0] * 7
    weekday_missed = [0] * 7
    for task in all_tasks:
        if not task.date:
            continue
        idx = task.date.weekday()
        if task.status == "done":
            weekday_done[idx] += 1
        elif task.status in ("missed_silent", "missed_excused"):
            weekday_missed[idx] += 1
    hour_done = _hour_done_from_log(point_log, timezone_name)
    bonus_offered, bonus_completed = bonus_counts or (0, 0)
    return RecapDashboard(
        total_tasks=total,
        completed_tasks=len(done),
        proofed_tasks=proofed,
        completion_rate=rate,
        category_counts=category_counts,
        points=dict(state.points),
        total_points=sum(state.points.get(c, 0) for c in CATEGORIES),
        streak_len=state.streak_len,
        best_streak=state.best_streak,
        days_in=max(days_in, 0),
        plans_count=len(all_plans),
        weekly_completed=weekly,
        mirror_line=_mirror_line(all_plans, state, start or (end - timedelta(days=6)), end),
        weekday_done=weekday_done,
        weekday_missed=weekday_missed,
        hour_done=hour_done,
        bonus_offered=bonus_offered,
        bonus_completed=bonus_completed,
        insights=_build_insights(
            weekday_done=weekday_done,
            weekday_missed=weekday_missed,
            hour_done=hour_done,
            bonus_offered=bonus_offered,
            bonus_completed=bonus_completed,
            state=state,
        ),
    )


def build_recap(
    *,
    state: GameState,
    plan: Plan | None,
    plans: list[Plan] | None = None,
    user_name: str = "",
    period: str = "14d",
    today: date | None = None,
    point_log: list[PointLogRecord] | None = None,
    timezone_name: str = "",
    bonus_counts: tuple[int, int] | None = None,
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
        dashboard=_build_dashboard(
            all_plans, state, days_in, end, start=start,
            point_log=point_log,
            timezone_name=timezone_name,
            bonus_counts=bonus_counts,
        ),
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
