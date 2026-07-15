#!/usr/bin/env python3
"""
.env dosyalarını düzenler: mevcut değerleri korur, bozuk formatı onarır.
Sırları stdout'a yazdırmaz. .env asla commit edilmez.
"""
from __future__ import annotations

import base64
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND_ENV = ROOT / ".env"
MOBILE_ENV = ROOT.parent / "mobile" / ".env"
JWKS_KID = "0b764915-f14d-49b0-b560-fed38eed6830"
JWKS_URL_SUFFIX = "/auth/v1/.well-known/jwks.json"


def _parse_env_lines(path: pathlib.Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        out[key.strip()] = value.strip()
    return out


def _jwt_role(token: str) -> str | None:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("role")
    except Exception:
        return None


def _split_supabase_blob(blob: str) -> dict[str, str]:
    """Birleştirilmiş anahtar satırını parçalar."""
    cleaned = blob.removeprefix("...").strip()
    parts = [p.strip() for p in cleaned.split("//") if p.strip()]
    found: dict[str, str] = {}
    for part in parts:
        if part.startswith("sb_secret_"):
            found["sb_secret"] = part
        elif part.startswith("sb_publishable_"):
            found["sb_publishable"] = part
        elif part.startswith("eyJ"):
            role = _jwt_role(part)
            if role == "service_role":
                found["jwt_service_role"] = part
            elif role == "anon":
                found["jwt_anon"] = part
    return found


def _railway_vars() -> dict[str, str]:
    try:
        from scripts.fetch_railway_env import fetch_service_variables

        return fetch_service_variables()
    except Exception:
        return {}


def _pick_service_key(existing_blob: str, railway: dict[str, str]) -> str:
    if railway.get("SUPABASE_SERVICE_KEY"):
        return railway["SUPABASE_SERVICE_KEY"]
    parts = _split_supabase_blob(existing_blob)
    return (
        parts.get("sb_secret")
        or parts.get("jwt_service_role")
        or ""
    )


def _pick_publishable(existing_blob: str, mobile_existing: dict[str, str]) -> str:
    mobile_key = mobile_existing.get("EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "")
    if mobile_key and not mobile_key.startswith("..."):
        return mobile_key
    parts = _split_supabase_blob(existing_blob)
    return parts.get("sb_publishable") or parts.get("jwt_anon") or ""


def organize_backend(existing: dict[str, str], railway: dict[str, str]) -> str:
    supabase_url = (
        existing.get("SUPABASE_URL")
        or railway.get("SUPABASE_URL")
        or ""
    )
    service_key = _pick_service_key(existing.get("SUPABASE_SERVICE_KEY", ""), railway)
    cron_secret = railway.get("CRON_SECRET") or existing.get("CRON_SECRET", "").removeprefix("...").strip()

    gemini_key = existing.get("GEMINI_API_KEY", "")
    unsplash_access = existing.get("UNSPLASH_ACCESS_KEY", "")
    unsplash_secret = existing.get("UNSPLASH_SECRET_KEY", "")

    return f"""# =============================================================================
# Niyetsen Backend — yerel geliştirme ortamı
# Bu dosya asla git'e commit edilmez. Düzenleme: python -m scripts.organize_env
# =============================================================================

# --- Ortam ---
ENV=dev
AUTH_DISABLED=true

# --- Gemini ---
GEMINI_API_KEY={gemini_key}
GEMINI_MODEL={existing.get("GEMINI_MODEL", "gemini-2.5-flash")}
GEMINI_MODEL_PLAN={existing.get("GEMINI_MODEL_PLAN", "gemini-2.5-pro")}
GEMINI_CHAT_MAX_OUTPUT_TOKENS={existing.get("GEMINI_CHAT_MAX_OUTPUT_TOKENS", "2048")}
GEMINI_PLAN_TIMEOUT_SEC={existing.get("GEMINI_PLAN_TIMEOUT_SEC", "90")}

# --- Unsplash ---
UNSPLASH_ACCESS_KEY={unsplash_access}
UNSPLASH_SECRET_KEY={unsplash_secret}

# --- Supabase (backend yalnızca service_role kullanır) ---
SUPABASE_URL={supabase_url}
SUPABASE_SERVICE_KEY={service_key}
USE_SUPABASE_DB={existing.get("USE_SUPABASE_DB", "true")}
# JWT: proje JWKS kullanıyor — doğrulama URL'si:
#   {{SUPABASE_URL}}{JWKS_URL_SUFFIX}
# kid: {JWKS_KID}
# Dev'de AUTH_DISABLED=true iken SUPABASE_JWT_SECRET boş kalabilir.
SUPABASE_JWT_SECRET=

# --- Cron (lokal test; Railway API ile aynı değer) ---
CRON_SECRET={cron_secret}

# --- CORS (web istemcisi; Expo Go native CORS kullanmaz) ---
CORS_ALLOWED_ORIGINS={existing.get("CORS_ALLOWED_ORIGINS", "http://localhost:8082,http://127.0.0.1:8082")}

# --- Plan / rate limit ---
PLAN_BATCH_DAYS={existing.get("PLAN_BATCH_DAYS", "7")}
MAX_TASKS_PER_DAY={existing.get("MAX_TASKS_PER_DAY", "5")}
CHAT_RATE_LIMIT_PER_MIN={existing.get("CHAT_RATE_LIMIT_PER_MIN", "10")}
PROOF_RATE_LIMIT_PER_MIN={existing.get("PROOF_RATE_LIMIT_PER_MIN", "5")}

# --- Hukuki metin sürümleri ---
PRIVACY_POLICY_VERSION={existing.get("PRIVACY_POLICY_VERSION", "2026-07-11")}
KVKK_CONSENT_VERSION={existing.get("KVKK_CONSENT_VERSION", "2026-07-11")}
AI_CHAT_CONSENT_VERSION={existing.get("AI_CHAT_CONSENT_VERSION", "2026-07-11")}
PROOF_PHOTO_CONSENT_VERSION={existing.get("PROOF_PHOTO_CONSENT_VERSION", "2026-07-11")}
MARKETING_CONSENT_VERSION={existing.get("MARKETING_CONSENT_VERSION", "2026-07-11")}
LEGAL_DATA_CONTROLLER={existing.get("LEGAL_DATA_CONTROLLER", "Şahin Çelebi")}
LEGAL_CONTACT_EMAIL={existing.get("LEGAL_CONTACT_EMAIL", "ai@niyetsen.com")}

# --- RevenueCat webhook (prod'da zorunlu; dev'de boş kalabilir) ---
REVENUECAT_WEBHOOK_SECRET={existing.get("REVENUECAT_WEBHOOK_SECRET", "")}
"""


def _is_service_key_material(key: str) -> bool:
    k = (key or "").strip()
    if not k:
        return False
    if k.startswith("sb_secret_"):
        return True
    if k.startswith("eyJ") and _jwt_role(k) == "service_role":
        return True
    return False


def _validate_mobile_publishable(key: str) -> str | None:
    k = (key or "").strip()
    if not k:
        return "EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY boş"
    if _is_service_key_material(k):
        return "mobil publishable alanı service_role/secret içeriyor"
    return None


def organize_mobile(
    backend_existing: dict[str, str],
    mobile_existing: dict[str, str],
    railway: dict[str, str],
) -> str:
    supabase_url = (
        mobile_existing.get("EXPO_PUBLIC_SUPABASE_URL")
        or backend_existing.get("SUPABASE_URL")
        or railway.get("SUPABASE_URL")
        or ""
    )
    publishable = _pick_publishable(
        backend_existing.get("SUPABASE_SERVICE_KEY", ""),
        mobile_existing,
    )
    api_url = mobile_existing.get(
        "EXPO_PUBLIC_API_URL",
        "https://api-production-86f1.up.railway.app",
    )

    return f"""# =============================================================================
# Niyetsen Mobile — Expo ortam değişkenleri
# Bu dosya asla git'e commit edilmez. Düzenleme: python -m scripts.organize_env
# =============================================================================

# --- Backend API ---
# Lokal backend: http://<LAN_IP>:8000  (ipconfig getifaddr en0)
# Prod Railway:
EXPO_PUBLIC_API_URL={api_url}

# --- Supabase (yalnızca publishable/anon — service_role ASLA buraya yazılmaz) ---
EXPO_PUBLIC_SUPABASE_URL={supabase_url}
EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY={publishable}

# --- PostHog (boşsa analitik kapalı) ---
EXPO_PUBLIC_POSTHOG_KEY={mobile_existing.get("EXPO_PUBLIC_POSTHOG_KEY", "")}
EXPO_PUBLIC_POSTHOG_HOST={mobile_existing.get("EXPO_PUBLIC_POSTHOG_HOST", "https://us.i.posthog.com")}

# --- RevenueCat (Expo Go'da IAP çalışmaz; EAS build gerekir) ---
EXPO_PUBLIC_REVENUECAT_API_KEY={mobile_existing.get("EXPO_PUBLIC_REVENUECAT_API_KEY", "")}
EXPO_PUBLIC_RC_ENTITLEMENT_ID={mobile_existing.get("EXPO_PUBLIC_RC_ENTITLEMENT_ID", "premium")}
"""


def main() -> int:
    backend_existing = _parse_env_lines(BACKEND_ENV)
    mobile_existing = _parse_env_lines(MOBILE_ENV)
    railway = _railway_vars()

    backend_content = organize_backend(backend_existing, railway)
    BACKEND_ENV.write_text(backend_content)

    if MOBILE_ENV.parent.exists():
        mobile_content = organize_mobile(backend_existing, mobile_existing, railway)
        MOBILE_ENV.write_text(mobile_content)

    # Doğrulama (sırları yazdırma)
    from app.config import settings

    issues: list[str] = []
    if not settings.SUPABASE_URL:
        issues.append("SUPABASE_URL boş")
    if not settings.SUPABASE_SERVICE_KEY:
        issues.append("SUPABASE_SERVICE_KEY boş")
    if settings.USE_SUPABASE_DB and not settings.SUPABASE_SERVICE_KEY:
        issues.append("USE_SUPABASE_DB=true ama service key yok")

    print("✅ niyetsen-backend/.env düzenlendi")
    if MOBILE_ENV.exists():
        print("✅ mobile/.env düzenlendi")
        mobile_parsed = _parse_env_lines(MOBILE_ENV)
        mobile_key_err = _validate_mobile_publishable(
            mobile_parsed.get("EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "")
        )
        if mobile_key_err:
            print(f"❌ Mobil Supabase anahtarı: {mobile_key_err}")
            return 1
        print("✅ Mobil env: yalnızca publishable/anon (service_role yok)")
    print(f"   GEMINI_API_KEY: {'dolu' if settings.GEMINI_API_KEY else 'boş'}")
    print(f"   SUPABASE_URL: {'dolu' if settings.SUPABASE_URL else 'boş'}")
    print(f"   SUPABASE_SERVICE_KEY: {'dolu' if settings.SUPABASE_SERVICE_KEY else 'boş'}")
    print(f"   CRON_SECRET: {'dolu' if settings.CRON_SECRET else 'boş'}")
    print(f"   UNSPLASH_ACCESS_KEY: {'dolu' if settings.UNSPLASH_ACCESS_KEY else 'boş'}")
    print(f"   UNSPLASH_SECRET_KEY: {'dolu' if backend_existing.get('UNSPLASH_SECRET_KEY') else 'boş'}")

    if issues:
        print("⚠️  " + "; ".join(issues))
        return 1

    try:
        from supabase import create_client

        db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        db.table("users").select("id").limit(1).execute()
        print("✅ Supabase bağlantı testi OK")
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Supabase bağlantı testi başarısız: {type(exc).__name__}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
