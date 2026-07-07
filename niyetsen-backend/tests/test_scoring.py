"""
Niyetsen — Puan/Zincir Motoru Testleri
Bu testler oyun kurallarının SÖZLEŞMESİDİR. Cursor bir şey değiştirdiğinde
bu dosya kırmızıya dönerse kural bozulmuş demektir. Çalıştır: pytest -q
"""
from datetime import date

from app.config import CATEGORIES
from app.models.schemas import GameState
from app.services import scoring_service as sc


def fresh(**kw) -> GameState:
    return GameState(user_id="t", **kw)


# ---------------- Puan kazanma ----------------
def test_complete_task_adds_50_per_category():
    s = fresh()
    sc.complete_task(s, ["İrade", "Sosyallik"])
    assert s.points["İrade"] == 50
    assert s.points["Sosyallik"] == 50
    assert s.points["Disiplin"] == 0


def test_complete_resets_silent_streak():
    s = fresh(silent_miss_streak=3)
    sc.complete_task(s, ["İrade"])
    assert s.silent_miss_streak == 0


def test_unknown_category_is_ignored():
    s = fresh()
    sc.complete_task(s, ["UydurmaKategori"])
    assert all(v == 0 for v in s.points.values())


# ---------------- Sessiz kaçırma: katlanma + TAVAN ----------------
def test_silent_penalty_doubles_then_caps_at_200():
    assert [sc.silent_penalty_amount(n) for n in range(6)] == [25, 50, 100, 200, 200, 200]


def test_silent_miss_applies_and_increments():
    s = fresh()
    s.points["İrade"] = 500
    sc.miss_task_silent(s, ["İrade"])   # -25
    sc.miss_task_silent(s, ["İrade"])   # -50
    sc.miss_task_silent(s, ["İrade"])   # -100
    assert s.points["İrade"] == 325
    assert s.silent_miss_streak == 3


def test_points_never_go_negative():
    s = fresh()
    s.points["İrade"] = 10
    s.silent_miss_streak = 3  # ceza 200 olurdu
    sc.miss_task_silent(s, ["İrade"])
    assert s.points["İrade"] == 0


def test_miss_task_silent_unknown_category_is_ignored():
    s = fresh()
    sc.miss_task_silent(s, ["UydurmaKategori"])
    assert all(v == 0 for v in s.points.values())
    assert s.silent_miss_streak == 1  # sayaç yine de artar, sadece puan etkilenmez


# ---------------- Mazeret yolu ----------------
def test_excuse_is_flat_25_and_resets_streak():
    s = fresh(silent_miss_streak=4)
    s.points["Disiplin"] = 100
    sc.miss_task_excused(s, ["Disiplin"])
    assert s.points["Disiplin"] == 75
    assert s.silent_miss_streak == 0
    assert s.excuse_count == 1


def test_tenth_excuse_halves_all_points_and_resets_counter():
    s = fresh(excuse_count=9)
    for c in CATEGORIES:
        s.points[c] = 1000
    sc.miss_task_excused(s, ["İrade"])  # önce -25, sonra tüm kategoriler ×0.5
    assert s.excuse_count == 0
    # İrade: 1000-25=975 → yarıya: 975 - 975//2 = 488
    assert s.points["İrade"] == 975 - (975 // 2)
    assert s.points["Disiplin"] == 1000 - (1000 // 2)


def test_ninth_excuse_does_not_trigger_halving():
    """Sınır testi: yarıya düşürme SADECE 10. mazerette tetiklenir, 9.'da değil."""
    s = fresh(excuse_count=8)
    for c in CATEGORIES:
        s.points[c] = 1000
    sc.miss_task_excused(s, ["İrade"])  # 9. mazeret: sadece sabit -25
    assert s.excuse_count == 9
    assert s.points["İrade"] == 975  # yarıya düşme YOK
    assert s.points["Disiplin"] == 1000  # diğer kategoriler hiç dokunulmadı


def test_miss_task_excused_unknown_category_is_ignored():
    s = fresh()
    sc.miss_task_excused(s, ["UydurmaKategori"])
    assert all(v == 0 for v in s.points.values())
    assert s.excuse_count == 1  # sayaç yine de artar, sadece puan etkilenmez
    assert s.silent_miss_streak == 0


# ---------------- Rank merdiveni ----------------
def test_rank_ladder():
    assert sc.rank_for(0) == "Çaylak"
    assert sc.rank_for(999) == "Çaylak"
    assert sc.rank_for(1000) == "Bronz III"
    assert sc.rank_for(4500) == "Silver III"
    assert sc.rank_for(9999) == "Gold I"
    assert sc.rank_for(10000) == "Usta"
    assert sc.rank_for(25000) == "Usta"


def test_overall_rank_is_average_tier():
    s = fresh()
    for c in CATEGORIES:
        s.points[c] = 3000
    assert sc.overall_rank(s.points) == "Bronz I"


# ---------------- Zincir ----------------
def test_streak_extends_on_consecutive_days():
    s = fresh()
    assert sc.close_day(s, date(2026, 7, 1), True) == "extended"
    assert sc.close_day(s, date(2026, 7, 2), True) == "extended"
    assert s.streak_len == 2 and s.best_streak == 2


def test_streak_restarts_after_gap():
    s = fresh()
    sc.close_day(s, date(2026, 7, 1), True)
    s.freeze_tokens = 0
    sc.close_day(s, date(2026, 7, 2), False)  # broken
    assert s.streak_len == 0
    sc.close_day(s, date(2026, 7, 3), True)
    assert s.streak_len == 1


def test_freeze_token_protects_empty_day():
    s = fresh()
    sc.close_day(s, date(2026, 7, 1), True)          # zincir 1, temmuz jetonu verildi
    tokens_before = s.freeze_tokens
    assert sc.close_day(s, date(2026, 7, 2), False) == "frozen"
    assert s.freeze_tokens == tokens_before - 1
    assert s.streak_len == 1                          # zincir korundu
    assert sc.close_day(s, date(2026, 7, 3), True) == "extended"
    assert s.streak_len == 2                          # korunan günden devam


def test_monthly_freeze_granted_once_per_month():
    s = fresh(freeze_tokens=0)
    assert sc.grant_monthly_freeze(s, date(2026, 7, 1)) is True
    assert sc.grant_monthly_freeze(s, date(2026, 7, 15)) is False
    assert sc.grant_monthly_freeze(s, date(2026, 8, 1)) is True
    assert s.freeze_tokens == 2


def test_close_day_idempotent_same_day():
    s = fresh()
    sc.close_day(s, date(2026, 7, 1), True)
    assert sc.close_day(s, date(2026, 7, 1), True) == "noop"
    assert s.streak_len == 1
