"""
Niyetsen — Function Calling Araç Seti (KAPALI LİSTE)
Model YALNIZCA bu araçları çağırabilir. Yeni araç eklemek = felsefe ihlali
kontrolü + Şahin onayı gerektirir (philosophy.py Yasa 4).

Cursor notu (v1): chat akışına bağlarken google-genai'de
  types.Tool(function_declarations=TOOL_DECLARATIONS)
olarak GenerateContentConfig'e verilir; dönen function_call'lar
HANDLERS sözlüğünden gerçek fonksiyonlara yönlenir (routes/chat üzerinden).
MVP'de chat bu araçları henüz kullanmaz; tanımlar hazır dursun diye buradadır.
"""
from __future__ import annotations

TOOL_DECLARATIONS = [
    {
        "name": "gorev_olustur",
        "description": "Kullanıcının planına yeni bir görev ekler.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "categories": {"type": "array", "items": {"type": "string"}},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "tiny_version": {"type": "string", "description": "2 dakikalık en küçük halka"},
            },
            "required": ["title", "categories", "date"],
        },
    },
    {
        "name": "kanit_dogrula",
        "description": "Yüklenen foto kanıtını görevle eşleştirir (backend Vision akışını tetikler).",
        "parameters": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "puan_guncelle",
        "description": "İlgili kategoriye puan ekler/düşer. Kurallar scoring_service'te; model miktar UYDURMAZ, sadece olayı bildirir.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "event": {"type": "string", "enum": ["complete", "miss_silent", "miss_excused"]},
            },
            "required": ["task_id", "event"],
        },
    },
    {
        "name": "gorev_ertele_mazeretli",
        "description": "Kullanıcı chat'te mazeret bildirdi: sabit ceza yolu (katlanma sıfırlanır).",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "excuse_text": {"type": "string"},
            },
            "required": ["task_id", "excuse_text"],
        },
    },
    {
        "name": "alarm_kur",
        "description": "Cihazda yerel alarm kurulmasını ister (mobil taraf uygular).",
        "parameters": {
            "type": "object",
            "properties": {"time": {"type": "string"}, "label": {"type": "string"}},
            "required": ["time", "label"],
        },
    },
    {
        "name": "takvime_ekle",
        "description": "Cihaz takvimine etkinlik eklenmesini ister (mobil taraf uygular).",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "date": {"type": "string"},
                "time": {"type": "string"},
            },
            "required": ["title", "date"],
        },
    },
    {
        "name": "etkinlik_olustur",
        "description": (
            "Bu plana fotosuz etkinlik/hatırlatma ekler (örn. 100 şınav, 23:00 uyku, "
            "her sabah yürüyüş). Yeni 365 plan üretmez. Tekrar: none (tek sefer), "
            "daily (her gün), weekdays (hafta içi), weekly (haftanın seçili günleri)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Kısa etkinlik adı"},
                "date": {
                    "type": "string",
                    "description": "YYYY-MM-DD başlangıç; söylenmediyse bugün",
                },
                "time": {"type": "string", "description": "HH:MM 24 saat"},
                "recurrence": {
                    "type": "string",
                    "enum": ["none", "daily", "weekdays", "weekly"],
                },
                "byweekday": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "weekly için 0=Pzt … 6=Paz",
                },
                "duration_min": {"type": "integer", "description": "Süre (dk)"},
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "İrade, İstikrar, Disiplin, Özgüven, Sosyallik, Özsaygı"
                    ),
                },
            },
            "required": ["title", "time"],
        },
    },
]

# Global /chat bu aracı görmez; plan-içi ajan görür (Şahin 2026-09-10).
PLAN_AGENT_TOOL_DECLARATIONS = [
    d for d in TOOL_DECLARATIONS if d["name"] in {
        "etkinlik_olustur", "alarm_kur", "takvime_ekle",
    }
]
GLOBAL_TOOL_DECLARATIONS = [
    d for d in TOOL_DECLARATIONS if d["name"] != "etkinlik_olustur"
]

ALLOWED_TOOL_NAMES = frozenset(d["name"] for d in TOOL_DECLARATIONS)


def is_allowed(tool_name: str) -> bool:
    """Model listede olmayan bir araç çağırırsa reddet (injection/uydurma önlemi)."""
    return tool_name in ALLOWED_TOOL_NAMES
