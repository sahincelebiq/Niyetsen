"""
Niyetsen — Uygulama Girişi
Çalıştır:  uvicorn app.main:app --reload
Swagger:   http://127.0.0.1:8000/docs
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import router
from app.config import settings
from app.core.observability import init_observability
from app.core.rate_limit import limiter

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
init_observability()

# GÜVENLİK KİLİDİ: prod'da auth kapalı çalıştırmak imkânsız olsun.
if settings.ENV == "prod" and settings.AUTH_DISABLED:
    raise RuntimeError(
        "ENV=prod iken AUTH_DISABLED=true olamaz. .env'de AUTH_DISABLED=false yap "
        "ve Supabase JWT doğrulamasını bağla (routes.get_current_user)."
    )

# GÜVENLİK KİLİDİ: prod'da bellek-içi depoyla çalışmak imkânsız olsun (veri kaybı).
if settings.ENV == "prod" and not settings.USE_SUPABASE_DB:
    raise RuntimeError(
        "ENV=prod iken USE_SUPABASE_DB=true olmalı. .env'de SUPABASE_SERVICE_KEY'i "
        "doldur ve USE_SUPABASE_DB=true yap."
    )

if settings.ENV == "prod" and not settings.CRON_SECRET:
    raise RuntimeError(
        "ENV=prod iken CRON_SECRET boş olamaz. Güçlü ve yalnız sunucuda tutulan "
        "bir cron sırrı yapılandır."
    )

if settings.ENV == "prod" and not settings.REVENUECAT_WEBHOOK_SECRET:
    raise RuntimeError(
        "ENV=prod iken REVENUECAT_WEBHOOK_SECRET boş olamaz. RevenueCat webhook "
        "doğrulaması zorunludur."
    )

app = FastAPI(
    title="Niyetsen API",
    version="0.1.0",
    description="Niyetini söze, sözünü zincire çevir. 🌙",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: dev'de varsayılan açık; prod'da yalnız yapılandırılmış web origin'leri.
# Native Expo/React Native istekleri tarayıcı CORS denetimine tabi değildir.
cors_origins = settings.CORS_ALLOWED_ORIGINS
if settings.ENV == "dev" and not cors_origins:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Store-hazırlık güvenlik katmanı (FAZ 7.5) ---------------------------
# 1) Gövde boyutu tavanı: multipart uçları kendi 5MB sınırını koyuyor; bu
#    katman TÜM uçlar için mutlak tavan (bellek DoS'una karşı ikinci hat).
MAX_REQUEST_BYTES = 10 * 1024 * 1024  # 10 MB


@app.middleware("http")
async def security_layer(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_REQUEST_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": "İstek gövdesi çok büyük."},
        )
    response = await call_next(request)
    # 2) Güvenlik başlıkları (API yanıtları için düşük maliyet, store/pentest
    #    kontrol listelerinde standart).
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path != "/health":
        # Kişisel veri taşıyan API yanıtları ara katmanlarda önbelleklenmesin.
        response.headers.setdefault("Cache-Control", "no-store")
    if settings.ENV == "prod":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
        )
    return response


# 3) Güvenli hata yanıtı: beklenmeyen exception'lar iç detay sızdırmaz;
#    tam iz log + Sentry'ye gider (observability init'te bağlı).
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.getLogger("niyetsen.app").exception(
        "İşlenmeyen hata: %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Beklenmeyen bir sorun oluştu. Birazdan tekrar dene."},
    )


app.include_router(router)
