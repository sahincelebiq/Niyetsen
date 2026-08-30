"""FAZ 4 fixed, non-medical micro-task pool."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BonusDefinition:
    key: str
    title: str
    category: str
    tiny_instruction: str


BONUS_POOL = (
    BonusDefinition("fresh-air", "Pencereyi aç ve bir dakika temiz hava al", "İrade", "Pencereye git."),
    BonusDefinition("water", "Bir bardak su hazırla ve iç", "Özsaygı", "Bardağı doldur."),
    BonusDefinition("desk", "Çalışma alanından üç gereksiz şeyi kaldır", "Disiplin", "Tek bir şeyi kaldır."),
    BonusDefinition("walk-five", "Kendine uygun tempoda beş dakika yürü", "İstikrar", "Ayakkabını hazırla."),
    BonusDefinition("stretch", "Bir dakika nazikçe esne", "Özsaygı", "Omuzlarını gevşet."),
    BonusDefinition("phone-away", "Telefonunu beş dakika uzağa bırak", "İrade", "Ekranı kapat."),
    BonusDefinition("gratitude", "Bugün iyi giden tek şeyi yaz", "Özgüven", "Bir kelime yaz."),
    BonusDefinition("read-two", "Seçtiğin kitaptan iki sayfa oku", "İstikrar", "Kitabı aç."),
    BonusDefinition("tomorrow", "Yarın için tek bir şeyi hazırla", "Disiplin", "Hazırlayacağın şeyi seç."),
    BonusDefinition("music", "Sana enerji veren bir şarkıyı dikkatle dinle", "Özsaygı", "Şarkıyı aç."),
    BonusDefinition("intention", "Bugünün niyetini tek cümleyle yaz", "İrade", "İlk üç kelimeyi yaz."),
    BonusDefinition("make-bed", "Yatağını veya dinlenme alanını toparla", "Disiplin", "Yastığı düzelt."),
    BonusDefinition("one-dish", "Bir bardak ya da tabağı temizle", "İstikrar", "Musluğu aç."),
    BonusDefinition("breathe", "Bir dakika rahat ritminde nefesine dön", "Özsaygı", "Tek nefesi fark et."),
    BonusDefinition("posture", "Duruşunu düzeltip omuzlarını gevşet", "Özgüven", "Omuzlarını indir."),
    BonusDefinition("message", "Değer verdiğin birine kısa bir selam gönder", "Sosyallik", "Kişiyi seç."),
    BonusDefinition("compliment", "Birine içten ve somut bir iltifat et", "Sosyallik", "Güzel bulduğun şeyi seç."),
    BonusDefinition("outside", "Mümkünse iki dakika gün ışığına çık", "İstikrar", "Kapıya yaklaş."),
    BonusDefinition("bag", "Çantandan gereksiz tek bir şeyi çıkar", "Disiplin", "Çantanı aç."),
    BonusDefinition("trash", "Yakınındaki bir çöpü yerine at", "İrade", "Bir tanesini seç."),
    BonusDefinition("close-tab", "Kullanmadığın üç sekmeyi veya uygulamayı kapat", "Disiplin", "Birini kapat."),
    BonusDefinition("mirror", "Kendinde takdir ettiğin bir özelliği söyle", "Özgüven", "Bir özellik seç."),
    BonusDefinition("pet", "Varsa evcil dostunla beş dakika ilgilen", "Sosyallik", "Yanına git."),
    BonusDefinition("quiet", "Bir dakika sessizce otur ve çevreni fark et", "Özsaygı", "Ekranı bırak."),
)


def pick_bonus(user_id: str, day: date, path_name: str = "") -> BonusDefinition:
    if path_name:
        from app.services.persona_service import _PATH_CATEGORIES, get_persona

        persona = get_persona(path_name)
        lessons = [
            str(item).strip()
            for item in ((persona.dossier.get("lessons_for_users") if persona else None) or [])
            if str(item).strip()
        ]
        if lessons:
            digest = hashlib.sha256(
                f"{user_id}:{day.isoformat()}:path:{path_name}".encode()
            ).digest()
            lesson = lessons[int.from_bytes(digest[:4], "big") % len(lessons)]
            category = "İstikrar"
            if persona:
                category = _PATH_CATEGORIES.get(persona.category, ["İstikrar"])[0]
            return BonusDefinition(
                key=f"path:{persona.slug if persona else 'yol'}",
                title=lesson[:80],
                category=category,
                tiny_instruction="Bu yolun bugünkü küçük adımı. Fotoğraf gerekmez.",
            )
    digest = hashlib.sha256(f"{user_id}:{day.isoformat()}".encode()).digest()
    return BONUS_POOL[int.from_bytes(digest[:4], "big") % len(BONUS_POOL)]


def is_completion_message(text: str) -> bool:
    normalized = " ".join((text or "").casefold().split())
    return normalized in {
        "yaptım", "yaptim", "tamamladım", "tamamladim",
        "bonus görevi yaptım", "bonus gorevi yaptim",
    }
