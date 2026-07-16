"""
Niyetsen — Yapılandırma
Tüm ayarlar tek yerden okunur. Sırlar YALNIZ .env'de yaşar (asla commit edilmez).
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes")


def _csv(name: str) -> list[str]:
    return [
        value.strip().rstrip("/")
        for value in os.environ.get(name, "").split(",")
        if value.strip()
    ]


class Settings:
    # --- AI ---
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_MODEL_PLAN: str = os.environ.get("GEMINI_MODEL_PLAN", "gemini-2.5-pro")
    GEMINI_TIMEOUT_SEC: int = int(os.environ.get("GEMINI_TIMEOUT_SEC", "30"))
    GEMINI_PLAN_TIMEOUT_SEC: int = int(os.environ.get("GEMINI_PLAN_TIMEOUT_SEC", "90"))
    # Vision kanıt: retry + ağ gecikmesi; mobil istemci ProofTimeoutMs ile uyumlu tut.
    GEMINI_PROOF_TIMEOUT_SEC: int = int(os.environ.get("GEMINI_PROOF_TIMEOUT_SEC", "45"))
    GEMINI_MAX_RETRIES: int = int(os.environ.get("GEMINI_MAX_RETRIES", "3"))
    GEMINI_CHAT_MAX_OUTPUT_TOKENS: int = int(
        os.environ.get("GEMINI_CHAT_MAX_OUTPUT_TOKENS", "2048")
    )
    # Nano Banana — plan görselleri (Unsplash ile hibrit)
    GEMINI_MODEL_IMAGE: str = os.environ.get(
        "GEMINI_MODEL_IMAGE", "gemini-2.5-flash-image"
    )
    GEMINI_IMAGE_TIMEOUT_SEC: int = int(os.environ.get("GEMINI_IMAGE_TIMEOUT_SEC", "60"))
    IMAGE_GEMINI_ENABLED: bool = _bool("IMAGE_GEMINI_ENABLED", "true")
    IMAGE_GEMINI_RATIO: float = float(os.environ.get("IMAGE_GEMINI_RATIO", "0.5"))

    # --- Görsel ---
    UNSPLASH_ACCESS_KEY: str = os.environ.get("UNSPLASH_ACCESS_KEY", "")

    # --- Ortam ---
    ENV: str = os.environ.get("ENV", "dev")  # dev | prod
    # Dev'de auth kapalı çalışabilir; PROD'DA ASLA. main.py bunu zorlar.
    AUTH_DISABLED: bool = _bool("AUTH_DISABLED", "true")
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    # service_role anahtarı — SADECE backend'de yaşar, RLS'i bypass eder, .env dışına çıkmaz.
    SUPABASE_SERVICE_KEY: str = (
        os.environ.get("SUPABASE_SERVICE_KEY", "")
        or os.environ.get("SUPABASE_SECRET_KEY", "")
    )
    SUPABASE_TIMEOUT_SEC: int = int(os.environ.get("SUPABASE_TIMEOUT_SEC", "120"))
    # false: InMemoryRepository (MVP varsayılanı, testler bunu kullanır).
    # true: SupabaseRepository — gerçek DB kalıcılığı (Faz 2).
    USE_SUPABASE_DB: bool = _bool("USE_SUPABASE_DB", "false")
    # Railway/Render cron'unun X-Cron-Secret başlığında gönderdiği sunucu sırrı.
    CRON_SECRET: str = os.environ.get("CRON_SECRET", "")
    # Web istemcilerinin tam origin listesi (virgülle ayrılmış). Native Expo
    # istekleri CORS'a tabi değildir. Dev'de boşsa wildcard kullanılır.
    CORS_ALLOWED_ORIGINS: list[str] = _csv("CORS_ALLOWED_ORIGINS")

    # --- MVP plan sınırları ---
    # 365 günü TEK istekte üretme (maliyet + timeout). Haftalık partiler halinde
    # üret; MVP'de ilk parti = 7 gün. (Cursor notu: uzun planlar için
    # plan_service.generate_next_batch yuvası hazır.)
    PLAN_BATCH_DAYS: int = int(os.environ.get("PLAN_BATCH_DAYS", "7"))
    MAX_TASKS_PER_DAY: int = int(os.environ.get("MAX_TASKS_PER_DAY", "5"))

    # --- Kanıt ---
    PROOF_MAX_BYTES: int = 5 * 1024 * 1024        # 5 MB
    PROOF_MIN_CONFIDENCE: int = 60                 # Gemini Vision güven eşiği
    PROOF_MAX_ATTEMPTS: int = 3                    # 3. denemede beyanla kabul

    # --- Rate limit (kullanıcı başına) ---
    CHAT_RATE_LIMIT_PER_MIN: int = int(os.environ.get("CHAT_RATE_LIMIT_PER_MIN", "10"))
    PROOF_RATE_LIMIT_PER_MIN: int = int(os.environ.get("PROOF_RATE_LIMIT_PER_MIN", "12"))
    PLAN_RATE_LIMIT_PER_MIN: int = int(os.environ.get("PLAN_RATE_LIMIT_PER_MIN", "3"))

    # --- Hukuki metin metadata'sı (metin değişince sürümü değiştir) ---
    PRIVACY_POLICY_VERSION: str = os.environ.get(
        "PRIVACY_POLICY_VERSION", "2026-07-11"
    )
    KVKK_CONSENT_VERSION: str = os.environ.get(
        "KVKK_CONSENT_VERSION", "2026-07-11"
    )
    AI_CHAT_CONSENT_VERSION: str = os.environ.get(
        "AI_CHAT_CONSENT_VERSION", "2026-07-11"
    )
    PROOF_PHOTO_CONSENT_VERSION: str = os.environ.get(
        "PROOF_PHOTO_CONSENT_VERSION", "2026-07-11"
    )
    MARKETING_CONSENT_VERSION: str = os.environ.get(
        "MARKETING_CONSENT_VERSION", "2026-07-11"
    )
    LEGAL_DATA_CONTROLLER: str = os.environ.get(
        "LEGAL_DATA_CONTROLLER", "Şahin Çelebi"
    )
    LEGAL_CONTACT_EMAIL: str = os.environ.get(
        "LEGAL_CONTACT_EMAIL", "ai@niyetsen.com"
    )

    # --- Abonelik (FAZ 5) ---
    REVENUECAT_WEBHOOK_SECRET: str = os.environ.get("REVENUECAT_WEBHOOK_SECRET", "")
    # Secret API key (dashboard) — /me/subscription/sync için; yalnız backend'de.
    REVENUECAT_API_KEY: str = os.environ.get("REVENUECAT_API_KEY", "")
    REVENUECAT_ENTITLEMENT_ID: str = os.environ.get("REVENUECAT_ENTITLEMENT_ID", "premium")

    # --- Gözlemlenebilirlik (FAZ 6) ---
    SENTRY_DSN: str = os.environ.get("SENTRY_DSN", "")

    # --- V2: RAG + Fal modülü (FAZ 7, 2026-07-16'da Şahin onayıyla başladı) ---
    RAG_ENABLED: bool = _bool("RAG_ENABLED", "true")
    # Embedding kapatılırsa keyword fallback çalışır (maliyet/kota kontrolü).
    RAG_EMBEDDINGS_ENABLED: bool = _bool("RAG_EMBEDDINGS_ENABLED", "true")
    RAG_TOP_K: int = int(os.environ.get("RAG_TOP_K", "4"))
    GEMINI_EMBED_MODEL: str = os.environ.get(
        "GEMINI_EMBED_MODEL", "gemini-embedding-001"
    )
    FORTUNE_RATE_LIMIT_PER_MIN: int = int(
        os.environ.get("FORTUNE_RATE_LIMIT_PER_MIN", "6")
    )


settings = Settings()


# ============================================================
# OYUN SABİTLERİ — MASTER_PLAN §1–2'den birebir. DEĞİŞTİRME.
# ============================================================
CATEGORIES = ["İrade", "İstikrar", "Disiplin", "Özgüven", "Sosyallik", "Özsaygı"]

POINTS_PER_TASK = 50          # görev tamamlama: etiketli her kategoriye +50
BONUS_POINTS = 10             # fotoğrafsız motivasyon bonus görevi
BASE_PENALTY = 25             # ceza tabanı
SILENT_PENALTY_CAP = 200      # sessiz kaçırma katlanma TAVANI (25→50→100→200)
EXCUSE_PENALTY = 25           # mazeret yolu: sabit, katlanmaz
EXCUSE_LIMIT = 10             # 10. mazerette tüm puan ×0.5, sayaç sıfırlanır
POINTS_FLOOR = 0              # puan asla negatif olmaz

# Rank merdiveni: eşik → kademe (kategori başına puanla)
RANK_LADDER = [
    (10_000, "Usta"),
    (9_000, "Gold I"), (8_000, "Gold II"), (7_000, "Gold III"),
    (6_000, "Silver I"), (5_000, "Silver II"), (4_000, "Silver III"),
    (3_000, "Bronz I"), (2_000, "Bronz II"), (1_000, "Bronz III"),
]
RANK_UNRANKED = "Çaylak"      # 1000 altı

FREEZE_TOKENS_PER_MONTH = 1   # Zincir Koruma Jetonu: ayda 1 otomatik

# --- V2 Fal hak sayaçları (docs/niyetsen-03-algoritma.md §5, günlük sıfırlanır) ---
# el_falı: ücretsiz 1, ücretli +2 · kahve: ücretsiz 1, ücretli +2 ("+ek" = +2
# yorumlandı, Şahin değiştirebilir) · tarot: herkese 1, EK YOK · burç: sınırsız.
FORTUNE_DAILY_RIGHTS = {
    "el":    {"free": 1, "premium": 3},
    "kahve": {"free": 1, "premium": 3},
    "tarot": {"free": 1, "premium": 1},
}
TAROT_CARDS_PER_DRAW = 3      # geçmiş · şimdi · niyetin yönü
