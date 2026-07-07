"""
Niyetsen — Uygulama Girişi
Çalıştır:  uvicorn app.main:app --reload
Swagger:   http://127.0.0.1:8000/docs
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings

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

app = FastAPI(
    title="Niyetsen API",
    version="0.1.0",
    description="Niyetini söze, sözünü zincire çevir. 🌙",
)

# CORS: Expo dev istemcileri için açık; prod'da domain listesine daralt.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENV == "dev" else [],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
