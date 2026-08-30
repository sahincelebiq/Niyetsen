from datetime import date

from app.config import CATEGORIES
from app.services.bonus_pool import BONUS_POOL, is_completion_message, pick_bonus


def test_bonus_pool_is_fixed_safe_and_category_bound():
    assert 20 <= len(BONUS_POOL) <= 30
    assert len({bonus.key for bonus in BONUS_POOL}) == len(BONUS_POOL)
    assert all(bonus.category in CATEGORIES for bonus in BONUS_POOL)
    assert all(bonus.title and bonus.tiny_instruction for bonus in BONUS_POOL)


def test_daily_bonus_selection_is_deterministic():
    day = date(2026, 7, 11)
    assert pick_bonus("user-1", day) == pick_bonus("user-1", day)


def test_path_bonus_uses_persona_lessons():
    from app.services import persona_service

    day = date(2026, 8, 30)
    persona = persona_service.get_persona("sisu-yolu")
    assert persona is not None
    lessons = [str(item).strip()[:80] for item in persona.dossier["lessons_for_users"]]
    flavored = pick_bonus("user-path", day, path_name="Sisu Yolu")
    generic = pick_bonus("user-path", day)
    assert flavored.title in lessons
    assert flavored.key.startswith("path:")
    assert flavored != generic


def test_completion_message_is_intentionally_narrow():
    assert is_completion_message("Yaptım")
    assert is_completion_message("bonus görevi yaptım")
    assert not is_completion_message("Yapmayı düşünüyorum")
    assert not is_completion_message("Arkadaşım yaptı")
