"""Niyetsen — profil/onboarding kuralları."""
from __future__ import annotations

from datetime import date, datetime, timezone

from app.models.schemas import ProfileUpdate, UserProfile


def zodiac_for(birth_date: date) -> str:
    month_day = (birth_date.month, birth_date.day)
    signs = [
        ((1, 20), "Kova"), ((2, 19), "Balık"), ((3, 21), "Koç"),
        ((4, 20), "Boğa"), ((5, 21), "İkizler"), ((6, 22), "Yengeç"),
        ((7, 23), "Aslan"), ((8, 23), "Başak"), ((9, 23), "Terazi"),
        ((10, 23), "Akrep"), ((11, 22), "Yay"), ((12, 22), "Oğlak"),
    ]
    sign = "Oğlak"
    for boundary, candidate in signs:
        if month_day >= boundary:
            sign = candidate
    return sign


def build_profile(update: ProfileUpdate, current: UserProfile) -> UserProfile:
    if update.birth_date > date.today():
        raise ValueError("Doğum tarihi gelecekte olamaz.")
    consent_at = current.kvkk_consent_at
    if update.kvkk_consent and consent_at is None:
        consent_at = datetime.now(timezone.utc)
    if consent_at is None:
        raise ValueError("Devam etmek için KVKK açık rızası gerekli.")

    return UserProfile(
        name=update.name.strip(),
        birth_date=update.birth_date,
        zodiac_sign=zodiac_for(update.birth_date),
        timezone=update.timezone,
        notif_hour=update.notif_hour,
        irade_modu_active=update.irade_modu_active,
        kvkk_consent_at=consent_at,
        onboarding_complete=True,
    )
