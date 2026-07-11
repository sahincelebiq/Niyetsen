"""
Niyetsen — Uygulama Girişi
Çalıştır:  uvicorn app.main:app --reload
Swagger:   http://127.0.0.1:8000/docs
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import router
from app.config import settings
from app.core.rate_limit import limiter

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

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

app.include_router(router)
