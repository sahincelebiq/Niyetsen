"""Saat dilimine ve kullanıcı bağlamına göre kişiselleştirilmiş sohbet karşılama."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.prompt_builder import normalize_app_locale


def _resolve_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name or "Europe/Istanbul")
    except ZoneInfoNotFoundError:
        return ZoneInfo("Europe/Istanbul")


_PACKS: dict[str, dict[str, str]] = {
    "tr": {
        "morning": "Günaydın",
        "afternoon": "İyi günler",
        "evening": "İyi akşamlar",
        "pending_streak": (
            "{opener} 🌙 {streak} günlük zincirin devam ediyor — "
            "bugün{plan_hint} {pending} görev seni bekliyor. "
            "Hazırsan küçük bir adımla başlayalım; takıldığın yerde buradayım."
        ),
        "pending": (
            "{opener} 🌙 Bugün{plan_hint} {pending} görev hazır. "
            "İlk küçük halkayı birlikte seçebiliriz — nasıl hissediyorsun?"
        ),
        "completed": (
            "{opener} 🌙 Bugünün halkalarını tamamladın. "
            "İstersen sohbet edelim veya yarının adımını birlikte seçelim."
        ),
        "needs_extension": (
            "{opener} 🌙 Planın duruyor; bugünün halkası henüz açılmamış. "
            "Bugün sekmesine geç — görevler orada belirecek. "
            "İstersen burada da yeni bir adım konuşabiliriz."
        ),
        "plan_streak": (
            "{opener} 🌙 {streak} günlük zincirin hâlâ yanında. "
            "Bugün için bekleyen görev görünmüyor — istersen sohbet edelim veya "
            "yeni bir adım planlayalım."
        ),
        "plan_idle": (
            "{opener} 🌙 Planın hazır; bugün için görev görünmüyor. "
            "İstersen sohbetten yeni bir adım ekleyebilir veya planını gözden geçirebiliriz."
        ),
        "fresh": (
            "{opener} 🌙 Ben Niyetsen. Bu yılı nasıl geçirmek istediğini birlikte "
            "konuşalım — hangi şehirdesin, neyle vakit geçirmeyi seviyorsun, "
            "haftada ne kadar zamanın var?"
        ),
    },
    "en-US": {
        "morning": "Good morning",
        "afternoon": "Good afternoon",
        "evening": "Good evening",
        "pending_streak": (
            "{opener} 🌙 Your {streak}-day streak is still going — "
            "today{plan_hint} {pending} tasks are waiting. "
            "When you are ready we can start with a small step; I am here if you get stuck."
        ),
        "pending": (
            "{opener} 🌙 Today{plan_hint} {pending} tasks are ready. "
            "We can pick the first small link together — how do you feel?"
        ),
        "completed": (
            "{opener} 🌙 You finished today’s links. "
            "We can talk, or choose tomorrow’s step together."
        ),
        "needs_extension": (
            "{opener} 🌙 Your plan is paused; today’s link is not open yet. "
            "Go to the Today tab — tasks will appear there. "
            "We can also talk about a new step here."
        ),
        "plan_streak": (
            "{opener} 🌙 Your {streak}-day streak is still with you. "
            "No pending task for today — we can chat or plan a new step."
        ),
        "plan_idle": (
            "{opener} 🌙 Your plan is ready; no task shows for today. "
            "We can add a step from chat or review the plan."
        ),
        "fresh": (
            "{opener} 🌙 I’m Niyetsen. Let’s talk about how you want to spend this year — "
            "which city you are in, what you enjoy, and how much time you have each week."
        ),
    },
    "en-GB": {
        "morning": "Good morning",
        "afternoon": "Good afternoon",
        "evening": "Good evening",
        "pending_streak": (
            "{opener} 🌙 Your {streak}-day streak is still going — "
            "today{plan_hint} {pending} tasks are waiting. "
            "When you are ready we can start with a small step; I am here if you get stuck."
        ),
        "pending": (
            "{opener} 🌙 Today{plan_hint} {pending} tasks are ready. "
            "We can pick the first small link together — how do you feel?"
        ),
        "completed": (
            "{opener} 🌙 You finished today’s links. "
            "We can talk, or choose tomorrow’s step together."
        ),
        "needs_extension": (
            "{opener} 🌙 Your plan is paused; today’s link is not open yet. "
            "Go to the Today tab — tasks will appear there. "
            "We can also talk about a new step here."
        ),
        "plan_streak": (
            "{opener} 🌙 Your {streak}-day streak is still with you. "
            "No pending task for today — we can chat or plan a new step."
        ),
        "plan_idle": (
            "{opener} 🌙 Your plan is ready; no task shows for today. "
            "We can add a step from chat or review the plan."
        ),
        "fresh": (
            "{opener} 🌙 I’m Niyetsen. Let’s talk about how you want to spend this year — "
            "which city you are in, what you enjoy, and how much time you have each week."
        ),
    },
    "de": {
        "morning": "Guten Morgen",
        "afternoon": "Guten Tag",
        "evening": "Guten Abend",
        "pending_streak": (
            "{opener} 🌙 Deine {streak}-Tage-Kette läuft weiter — "
            "heute{plan_hint} warten {pending} Aufgaben. "
            "Wenn du bereit bist, starten wir mit einem kleinen Schritt; ich bin da."
        ),
        "pending": (
            "{opener} 🌙 Heute{plan_hint} sind {pending} Aufgaben bereit. "
            "Das erste kleine Glied können wir zusammen wählen — wie fühlst du dich?"
        ),
        "completed": (
            "{opener} 🌙 Du hast die Glieder von heute erledigt. "
            "Wir können reden oder den Schritt für morgen wählen."
        ),
        "needs_extension": (
            "{opener} 🌙 Dein Plan steht still; das Glied von heute ist noch nicht offen. "
            "Geh zum Tab Heute — dort erscheinen die Aufgaben. "
            "Hier können wir auch einen neuen Schritt sprechen."
        ),
        "plan_streak": (
            "{opener} 🌙 Deine {streak}-Tage-Kette ist noch bei dir. "
            "Für heute ist keine Aufgabe offen — wir können reden oder einen neuen Schritt planen."
        ),
        "plan_idle": (
            "{opener} 🌙 Dein Plan ist bereit; für heute zeigt sich keine Aufgabe. "
            "Wir können im Chat einen Schritt ergänzen oder den Plan ansehen."
        ),
        "fresh": (
            "{opener} 🌙 Ich bin Niyetsen. Lass uns sprechen, wie du dieses Jahr leben willst — "
            "in welcher Stadt du bist, was du gern tust, und wie viel Zeit du pro Woche hast."
        ),
    },
    "fr": {
        "morning": "Bonjour",
        "afternoon": "Bon après-midi",
        "evening": "Bonsoir",
        "pending_streak": (
            "{opener} 🌙 Ta chaîne de {streak} jours continue — "
            "aujourd’hui{plan_hint} {pending} tâches t’attendent. "
            "Quand tu es prêt, on commence par un petit pas ; je suis là."
        ),
        "pending": (
            "{opener} 🌙 Aujourd’hui{plan_hint} {pending} tâches sont prêtes. "
            "On peut choisir le premier petit maillon ensemble — comment tu te sens ?"
        ),
        "completed": (
            "{opener} 🌙 Tu as terminé les maillons du jour. "
            "On peut parler, ou choisir ensemble le pas de demain."
        ),
        "needs_extension": (
            "{opener} 🌙 Ton plan est en pause ; le maillon du jour n’est pas encore ouvert. "
            "Va dans l’onglet Aujourd’hui — les tâches apparaîtront là. "
            "On peut aussi parler d’un nouveau pas ici."
        ),
        "plan_streak": (
            "{opener} 🌙 Ta chaîne de {streak} jours est encore avec toi. "
            "Aucune tâche en attente aujourd’hui — on peut parler ou planifier un nouveau pas."
        ),
        "plan_idle": (
            "{opener} 🌙 Ton plan est prêt ; aucune tâche ne s’affiche pour aujourd’hui. "
            "On peut ajouter un pas depuis le chat ou revoir le plan."
        ),
        "fresh": (
            "{opener} 🌙 Je suis Niyetsen. Parlons de l’année que tu veux vivre — "
            "dans quelle ville tu es, ce que tu aimes, et combien de temps tu as chaque semaine."
        ),
    },
    "ar": {
        "morning": "صباح الخير",
        "afternoon": "طاب يومك",
        "evening": "مساء الخير",
        "pending_streak": (
            "{opener} 🌙 سلسلتك لـ {streak} يومًا ما زالت مستمرة — "
            "اليوم{plan_hint} تنتظرك {pending} مهام. "
            "عندما تكون جاهزًا نبدأ بخطوة صغيرة؛ أنا هنا إن تعثرت."
        ),
        "pending": (
            "{opener} 🌙 اليوم{plan_hint} جاهزة {pending} مهام. "
            "يمكننا اختيار الحلقة الصغيرة الأولى معًا — كيف تشعر؟"
        ),
        "completed": (
            "{opener} 🌙 أنهيت حلقات اليوم. "
            "يمكننا الحديث، أو اختيار خطوة الغد معًا."
        ),
        "needs_extension": (
            "{opener} 🌙 خطتك متوقفة؛ حلقة اليوم لم تُفتح بعد. "
            "انتقل إلى تبويب اليوم — ستظهر المهام هناك. "
            "ويمكننا أيضًا الحديث عن خطوة جديدة هنا."
        ),
        "plan_streak": (
            "{opener} 🌙 سلسلتك لـ {streak} يومًا ما زالت معك. "
            "لا مهمة معلّقة اليوم — يمكننا الحديث أو تخطيط خطوة جديدة."
        ),
        "plan_idle": (
            "{opener} 🌙 خطتك جاهزة؛ لا مهمة ظاهرة لليوم. "
            "يمكننا إضافة خطوة من المحادثة أو مراجعة الخطة."
        ),
        "fresh": (
            "{opener} 🌙 أنا نيّة سن. لنتحدث كيف تريد أن تعيش هذه السنة — "
            "في أي مدينة أنت، ماذا تحب، وكم من الوقت لديك كل أسبوع."
        ),
    },
}


def _pack_for(locale: str) -> dict[str, str]:
    canonical = normalize_app_locale(locale) or "tr"
    return _PACKS.get(canonical) or _PACKS["tr"]


def _salutation_for_hour(hour: int, pack: dict[str, str]) -> str:
    if 5 <= hour < 12:
        return pack["morning"]
    if 12 <= hour < 18:
        return pack["afternoon"]
    return pack["evening"]


def _name_clause(name: str | None) -> str:
    trimmed = (name or "").strip()
    return f" {trimmed}" if trimmed else ""


def build_chat_greeting(
    *,
    name: str | None,
    timezone_name: str,
    streak_len: int = 0,
    pending_tasks_today: int = 0,
    completed_tasks_today: int = 0,
    needs_extension: bool = False,
    active_plan_name: str = "",
    has_plan: bool = False,
    locale: str = "tr",
) -> str:
    """KULLANICI BELLEĞİ'nin sohbet girişine yansıması — zincir + bugün nabzı."""
    pack = _pack_for(locale)
    local_now = datetime.now(timezone.utc).astimezone(_resolve_timezone(timezone_name))
    salutation = _salutation_for_hour(local_now.hour, pack)
    opener = f"{salutation}{_name_clause(name)}!"
    plan_hint = f" ({active_plan_name})" if active_plan_name.strip() else ""
    ctx = {
        "opener": opener,
        "streak": streak_len,
        "pending": pending_tasks_today,
        "plan_hint": plan_hint,
    }

    if has_plan and pending_tasks_today > 0:
        key = "pending_streak" if streak_len > 0 else "pending"
        return pack[key].format(**ctx)

    if has_plan and completed_tasks_today > 0:
        return pack["completed"].format(**ctx)

    if has_plan and needs_extension:
        return pack["needs_extension"].format(**ctx)

    if has_plan and streak_len > 0:
        return pack["plan_streak"].format(**ctx)

    if has_plan:
        return pack["plan_idle"].format(**ctx)

    return pack["fresh"].format(**ctx)
